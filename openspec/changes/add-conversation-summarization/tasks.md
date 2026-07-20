# Implementation Tasks

## 1. State & config

- [x] 1.1 Add `conversation_summary: str | None` and `last_prompt_tokens: int` fields to
      `EmailState` ([src/agent/state.py](src/agent/state.py)). Both plain JSON; `last_prompt_tokens`
      needs a reducer-free default (0) — give it a default in the type or via `field(default=0)`
      semantics consistent with the existing `total=False` schema.
- [x] 1.2 Add settings `summarize_token_threshold: int = 100000` and
      `summarize_keep_last_messages: int = 6` to `Settings` ([src/config.py](src/config.py)).
- [x] 1.3 Mirror both settings in [config.yaml](config.yaml) with Russian comments.
- [x] 1.4 `uv run alembic check` — confirm no model/DB drift (no migration expected; fields live
      in existing JSONB).

## 2. Summarization prompt

- [x] 2.1 Create [src/agent/prompts/system_summarize.md](src/agent/prompts/system_summarize.md):
      one-shot hidden call. Lead with current goal + immediate next step; preserve booking facts,
      hotel email + source, outbound emails (subject/gist/`message_id`), inbound hotel replies +
      decisions, scheduled tasks, guest wishes, open questions; compress small talk over facts.
      Note (for the writer) that booking fields/timezones/`message_id` also live in `EmailState` —
      mention for continuity, don't treat messages as the only source.
- [x] 2.2 Export it from `src/agent/prompts/__init__.py` alongside `SYSTEM_MAIN`/`SYSTEM_LETTER_TO_HOTEL`.

## 3. Summarization logic module

- [x] 3.1 Create [src/agent/summarization.py](src/agent/summarization.py) (parallel to
      `compaction.py`):
      - `summarization_needed(last_prompt_tokens: int, threshold: int) -> bool`;
      - `split_index(messages, keep_last) -> int` — returns the recency cut, **with the tool-call
        guard**: if the cut lands between an `AIMessage(tool_calls)` and its `ToolMessage`(s),
        move it back to that `AIMessage`. Never split a pair.
      - `summarize_prefix(messages, prev_summary) -> str` — builds the one-shot invoke input
        (`[SUMMARIZE_PROMPT, *(SystemMessage(prev) if prev else []), *prefix]`), returns the
        summary text. Fetches the model via `get_context()`.
      Pure helpers (`split_index`, `summarization_needed`) take/return plain data; only
      `summarize_prefix` touches `get_context()`.

## 4. Graph wiring

- [x] 4.1 In [src/agent/agent.py](src/agent/agent.py):
      - in `model_node`, after `result = await model.ainvoke(...)`, read
        `result.usage_metadata["input_tokens"]` and return it in the state update as
        `last_prompt_tokens`; prepend `conversation_summary` as a `SystemMessage` right after
        `SYSTEM_MAIN` in the invoke input.
      - add `summarize_check(state) -> Literal["summarize", "model"]` conditional reading
        `last_prompt_tokens` vs `get_settings().summarize_token_threshold`.
      - add `summarize_node(state)` — send the guest notification (`send_telegram_reply`), compute
        `split_index`, call `summarize_prefix`, return
        `{"conversation_summary": new_summary, "messages": [RemoveMessage(id=m.id) for m in prefix]}`.
      - rewire edges: `START → summarize_check`; `tools → summarize_check` (was `tools → model`);
        `summarize_check → summarize → model` and `summarize_check → model`.
      - register `summarize` node with full LLM activity metadata (own
        `start_to_close_timeout = llm_activity_timeout_seconds`, retry policy, Langfuse via
        `@with_langfuse`).
- [x] 4.2 `uv run ruff check && uv run ruff format` on touched files.
- [x] 4.3 `uv run ty check` — no new diagnostics in `src/`.

## 5. Tests (integration-flavored, on mocks)

- [x] 5.1 `tests/test_conversation_summarization.py` — drive a compiled `StateGraph(EmailState)`
      mirroring `build_email_agent`'s shape (scripted fake chat model + real `add_messages`
      reducer, mock boundary = the fake model, not respx). Cover:
      - over-threshold `last_prompt_tokens` routes `summarize_check → summarize → model`; prefix
        messages removed via `RemoveMessage`, recency window retained, `conversation_summary` set
        and prepended on the following model invoke;
      - under-threshold routes straight to `model`;
      - **tool-call guard**: cut landing between an `AIMessage(tool_calls)` and its `ToolMessage`
        is moved back so the pair stays together;
      - re-summarization includes the prior summary in the input.
- [x] 5.2 `uv run pytest tests/test_conversation_summarization.py -q` green.

## 6. Docs

- [x] 6.1 Update [docs/agent.md](docs/agent.md): new node `summarize`, the
      `summarize_check → summarize → model` routing, the `conversation_summary` /
      `last_prompt_tokens` state fields, signal-from-`usage_metadata`, recency-window +
      tool-call guard, notification. Place near the `cleanup` section (both are context
      management) but make clear they are orthogonal mechanisms.
- [x] 6.2 Update [docs/architecture.md](docs/architecture.md): graph diagram now includes the
      `summarize_check`/`summarize` leg; mention the new state fields are plain JSON (no
      converter change).
- [x] 6.3 Update [CLAUDE.md](CLAUDE.md): Architecture section — add a "Conversation summarization"
      paragraph (soft threshold from `usage_metadata`, running summary field, RemoveMessage +
      recency window, tool-call guard, notification); cross-link `summarization.py`.

## 7. Verify & ship

- [x] 7.1 `uv run ruff check && uv run ruff format && uv run ty check && uv run alembic check`
      all clean.
- [ ] 7.2 Local smoke: `docker compose up -d postgres temporal`, run app, drive a long thread past
      the threshold, confirm summarization fires, guest is notified, and the agent continues
      coherently.
- [ ] 7.3 Commit on `main`, deploy
      `env -u RAILWAY_TOKEN -u RAILWAY_API_TOKEN railway up --service app --detach -m "feat: conversation summarization"`,
      poll `env -u RAILWAY_TOKEN -u RAILWAY_API_TOKEN railway deployment list --service app --json`
      to `SUCCESS`.
