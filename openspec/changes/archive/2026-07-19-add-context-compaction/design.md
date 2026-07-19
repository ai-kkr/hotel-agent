## Context

`search_internet` and `extract_web_page` ([src/agent/tools/search.py](src/agent/tools/search.py))
return full Tavily payloads as `ToolMessage`s into `EmailState.messages`. That list is persisted as
JSONB in `states` (`StateType`, [src/db/types.py](src/db/types.py)) and reloaded on every subsequent
turn of the same client thread — so a one-shot search blob keeps costing tokens and latency across
the whole conversation. The agent has already pulled what it needs (hotel email/website/…) into the
structured booking fields via `set_booking_info`; the raw text is disposable after the turn that
produced it.

Current graph ([src/agent/agent.py](src/agent/agent.py)):

```
add_edge(START, "model")
add_conditional_edges("model", tool_path)   # tools_condition → "tools" | "__end__"
add_edge("tools", "model")
```

`messages` uses LangGraph's stock `add_messages` reducer (inherited from
`langchain.agents.AgentState`). Per the official docs, `add_messages` **updates an existing message
in place when the incoming message has the same `id`** (ID-based dedup/upsert). This is the lever we
use — no custom reducer needed.

## Goals / Non-Goals

**Goals:**

- Replace disposable search/extract `ToolMessage` content with a short stub **in place**, at the
  end of the turn that produced it, so future turns load lighter state.
- Preserve message identity (`id`), tool-call linkage (`tool_call_id`), and tool name (`name`) so
  provider tool-call ↔ tool-response invariants and LangGraph's own bookkeeping stay intact.
- Make compaction idempotent across turns (a stub is never re-processed).
- Keep `messages` on the stock `add_messages` reducer; do not touch the workflow↔activity data
  converter or the persistence schema.

**Non-Goals:**

- No LLM-generated digest of the archived content — the stub is a fixed string.
- No compaction of non-search messages (hotel replies, guest forwards, agent replies, booking
  confirmations).
- No migration, no new env var / `config.yaml` knob.
- No mid-turn compaction — within a turn the model may still need the raw results to act on them.

## Decisions

### D1. In-place id-upsert (not a custom reducer, not `RemoveMessage`)

The cleanup node returns `{"messages": [stub, …]}` where each stub reuses the heavy message's
`id`. `add_messages` then overwrites the heavy message in place. Considered alternatives:

- **Custom `messages` reducer + sentinel message** (the originally discussed idea): more
  declarative ("archive everything eligible"), but requires re-implementing `add_messages`
  semantics (id dedup, `RemoveMessage` handling) inside our reducer and risks the sentinel not
  round-tripping through `StateType` / `message_aware_data_converter`. Rejected — id-upsert gives
  the same effect with zero reducer surface.
- **`RemoveMessage` + append stub**: `RemoveMessage` *deletes*; the stub would land at the end,
  not in place, breaking the tool-call ordering invariant some providers enforce. Rejected.

We reuse the heavy message's existing `id` verbatim — so we do not depend on *how* `ToolNode`
assigns ids (random uuid vs tool-call-id). Whatever it is, we copy it.

### D2. Idempotency marker in `additional_kwargs`

Each stub carries `additional_kwargs={"archived": True}`. The node skips any message already marked.
`additional_kwargs` is a plain `dict[str, Any]` on `BaseMessage`, already JSON-serialized by
langchain's `messages_to_dict`, so it round-trips through `StateType` (DB JSONB) and through
`message_aware_data_converter` ([src/temporal/converter.py](src/temporal/converter.py)) with **no
new non-JSON field** and **no converter change**. The data converter re-validates message-shape
dicts; a `ToolMessage` with `additional_kwargs` is normal input, so it passes.

### D3. Whitelist by tool `name`, not by content size

`ARCHIVABLE_TOOLS = frozenset({"search_internet", "extract_web_page"})`. We match
`ToolMessage.name`, never a length threshold — a long hotel reply must never be compacted. Adding a
future tool to the archive set is a one-line whitelist edit. (Whitelist membership is also exactly
the predicate for the shortcut below.)

### D4. One new node `cleanup`, plus a shortcut in the conditional edge

```
        ┌─────────────────────────────────────────────┐
        │                                             ▼
START → model ──tool_path──▶ tools ──────────────── model
        │
        └─(нет tool_calls)──▶ cleanup ──▶ END
```

`tool_path` returns one of `"tools"`, `"cleanup"`, or `"__end__"`:

- model emitted tool calls → `"tools"` (unchanged).
- model emitted no tool calls **and** state has ≥1 un-archived `ToolMessage` with
  `name ∈ ARCHIVABLE_TOOLS` → `"cleanup"`.
- otherwise (no tool calls, nothing to archive) → `"__end__"` directly (the **shortcut**: no
  cleanup activity scheduled).

This honors rule "prefer reusing the existing graph" — we add exactly one node and one edge
(`cleanup → END`), and reroute the model's terminal conditional branch. We do **not** add a tool to
`src/agent/tools/`; `cleanup` is a graph node returning a plain state update (not
`Command(update=...)` for tool-call semantics).

### D5. Placement of compaction logic

A small helper module `src/agent/compaction.py` holds:

- `ARCHIVABLE_TOOLS` constant,
- the `additional_kwargs` key `"archived"` (named constant, not a magic string),
- `compaction_needed(messages) -> bool` (the shortcut predicate), and
- `compact(messages) -> list[ToolMessage]` (returns only the stubs to emit — empty list when
  nothing to do).

The node in `agent.py` is a thin wrapper: read `state["messages"]`, call `compact(...)`, return
`{"messages": stubs}` (or `{}` when empty). Node runs as a Temporal activity like the others; since
it is pure Python with no LLM call, its `start_to_close_timeout` can be small (seconds) rather than
the LLM-scaled `llm_activity_timeout_seconds`.

### D6. Flat-data / lazy-deps rule

`cleanup` touches only `EmailState.messages` (plain langchain messages already in state). It needs
no chat model, Mailtrap, Tavily, or session factory — so it does **not** reach into `get_context()`
at all, and passes no live object through state/context. The rule is trivially satisfied.

## Risks / Trade-offs

- **[A future search-style tool whose output is NOT captured in structured state]** → it would be
  wrongly archived. *Mitigation:* the whitelist is explicit by `name`; only add a tool to it once
  its output is confirmed disposable. Documented in the spec.
- **[Stub loses info the model wanted to revisit next turn]** → possible if the agent ends a turn
  mid-investigation. *Mitigation:* a turn only ends when the model stops calling tools and replies
  — by then the agent either committed findings to state or chose to stop. Acceptable; richer
  stubs (digest) are a later change if it bites.
- **[Provider rejects a tool_call whose matching ToolMessage content changed]** → low: content is
  free-form; only `id`/`tool_call_id`/order matter, and all are preserved. *Mitigation:* covered by
  an integration test driving a real turn through the graph with a stubbed model.
- **[id-upsert does not fire because the heavy ToolMessage has no `id`]** → we always copy
  `msg.id`; if it were `None` for some message, `add_messages` falls back to append (no replace,
  no harm — just no compaction for that one). *Mitigation:* assert in tests that search ToolMessages
  carry an `id` in practice.

## Migration Plan

- Pure code change; no schema migration, no env var, no `config.yaml` delta.
- Existing persisted `states` rows (with un-compacted history) are unaffected: on the next turn the
  cleanup node will simply archive whatever is eligible at that turn's end. No backfill needed.
- Deploy: standard `railway up --service app --detach -m "…"`; dev/prod contours isolated, no
  stop-other-instance coordination. Rollback = revert the deploy (state shape unchanged).

## Open Questions

- Stub wording: fixed `"[архив: результаты поиска]"` for both tools, or per-tool
  (`"[архив: текст страницы]"` for `extract_web_page`)? Lean toward per-tool for clarity — decide
  in tasks.
- Should `cleanup` log (structlog) how many messages it compacted, for observability? Lean yes.
