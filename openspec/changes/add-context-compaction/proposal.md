## Why

The agent accumulates heavy `ToolMessage`s in `EmailState.messages` — full Tavily search
results (`search_internet`) and extracted web-page text (`extract_web_page`). These blobs are
persisted in the `states` table (JSONB) and re-sent to the LLM on **every subsequent turn** of
the same client conversation, even though the agent has already extracted what it needed (hotel
email, website, …) into the structured booking fields. The raw text is one-shot: it just inflates
token cost and latency for the rest of the thread. We compact it away at the end of the turn that
produced it.

## What Changes

- Add a **cleanup node** to the agent graph that runs once at the very end of a turn — the path
  to `END` now goes `model → cleanup → END` (only when the model stops calling tools), instead of
  `model → END` directly.
- The node walks `state["messages"]`, finds `ToolMessage`s from the **archive whitelist**
  (`search_internet`, `extract_web_page`) that have not yet been compacted, and replaces each
  **in place** with a short stub via the built-in `add_messages` **id-upsert** (same `id` ⇒
  overwrite). No custom reducer on `messages`; we keep using `langchain.agents.AgentState`'s
  `add_messages`.
- Each stub keeps the original `id`, `tool_call_id`, and `name` (so the `tool_call ↔ response`
  linkage providers require stays intact) and carries a sentinel marker
  `additional_kwargs["archived"] = True` so the node skips already-compacted stubs on later turns.
- **Shortcut:** when the turn produced no archive-eligible tool calls and there are no
  un-archived eligible messages in state, `cleanup` is skipped entirely (decided in the
  conditional edge from `model`, not by running a no-op activity).

Non-goals:

- No summarization / no LLM call inside cleanup — the stub is a fixed string
  (`"[архив: результаты поиска]"`-style), not a generated digest. (Richer stubs are a possible
  later change.)
- No compaction of other message types (hotel replies, guest forwards, booking confirmations,
  the agent's own replies) — only the two search/extract tools.
- No schema/migration, no new env var, no new tool.

## Capabilities

### New Capabilities

- `context-compaction`: end-of-turn compaction of disposable tool-output messages
  (search/extract results), reducing per-turn token cost in long conversations without losing
  conversation structure or tool-call linkage.

### Modified Capabilities

None. (`scheduled-tasks` is untouched.)

## Impact

**Code:**

- `src/agent/agent.py` — new `cleanup` node; `tool_path` / conditional edges re-wired so the
  no-tool-calls branch routes to `cleanup → END`; the shortcut decision lives here.
- A small helper module for the compaction logic (whitelist constant, the
  `additional_kwargs["archived"]` marker, the stub builder) — placement TBD in design.

**Risk areas (per project rules):**

- **Agent state serializability / Temporal boundary:** the only state change is replacing
  message *content* (and adding a string marker) on existing `ToolMessage`s; types are unchanged,
  no new non-JSON field. `additional_kwargs` round-trips through `messages_to_dict`/
  `messages_from_dict` (`StateType`, `src/db/types.py`) and through `message_aware_data_converter`
  (`src/temporal/converter.py`) because stubs are plain `ToolMessage`s. No new data crosses the
  workflow↔activity boundary.
- **`messages` reducer:** deliberately NOT overridden — we rely on `add_messages` id-upsert. No
  behavior change to dedup / `RemoveMessage` handling.
- **Email threading:** untouched.

**New tool in `src/agent/tools/`:** none — `cleanup` is a graph node, not a tool, and does not
return `Command(update=...)` for tool-call semantics (it returns a normal state update
`{"messages": [stubs...]}`).

**Deployment:**

- No Alembic migration, no new `KKR_*` env var, no `config.yaml` addition (cleanup is fixed
  logic, not tunable). Standard `railway up --service app --detach` deploy; dev and prod contours
  are isolated (separate bot tokens), so no stop-the-other-instance coordination needed.
