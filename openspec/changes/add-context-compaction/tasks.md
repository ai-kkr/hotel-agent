## 1. Compaction helper

- [x] 1.1 Create `src/agent/compaction.py`: `ARCHIVABLE_TOOLS = frozenset({"search_internet", "extract_web_page"})`, marker key constant `ARCHIVED_KWARG = "archived"`, per-tool stub strings (e.g. `"[архив: результаты поиска]"` for search, `"[архив: текст страницы]"` for extract).
- [x] 1.2 Implement `compaction_needed(messages) -> bool` — True iff any `ToolMessage` has `name ∈ ARCHIVABLE_TOOLS` and `additional_kwargs.get(ARCHIVED_KWARG)` is falsy.
- [x] 1.3 Implement `compact(messages) -> list[ToolMessage]` — for each eligible un-archived message, build a stub `ToolMessage` copying the original `id`, `tool_call_id`, `name`, with stub content and `additional_kwargs={ARCHIVED_KWARG: True}`; return only the stubs (empty list when nothing to compact).

## 2. Wire the cleanup node + shortcut

- [x] 2.1 In `src/agent/agent.py` add a `cleanup_node(state) -> EmailState` that reads `state["messages"]`, calls `compact(...)`, logs (structlog) how many were compacted, and returns `{"messages": stubs}` (or `{}` when empty). No `get_context()`, no LLM.
- [x] 2.2 Update `tool_path` to return `"tools"` / `"cleanup"` / `"__end__"`: tool calls → `"tools"`; no tool calls + `compaction_needed(state)` → `"cleanup"`; else → `"__end__"` (shortcut).
- [x] 2.3 Register the node in `build_email_agent`: `workflow.add_node("cleanup", cleanup_node, metadata=common)` with a small `start_to_close_timeout` (seconds, not LLM-scaled); `add_edge("cleanup", END)`; replace the model's terminal conditional so the no-tool-calls branch routes to `cleanup` instead of `__end__`.
- [x] 2.4 Import `END` from `langgraph.graph` alongside `START`.

## 3. Tests (integration-flavored, on mocks)

- [x] 3.1 Add `tests/test_context_compaction.py`: drive the agent graph through a real turn — a deterministic fake chat model that first emits a `search_internet` tool call, then a final no-tool reply; Tavily HTTP mocked with `respx`. Assert the search `ToolMessage` is replaced in place by a stub with the same `id`/`tool_call_id`/`name` and `additional_kwargs["archived"] is True`, and that the stub content is the short string.
- [x] 3.2 Same test fixture, second turn: fake model replies with no tool calls and state already contains only archived stubs — assert the graph takes the shortcut (`model → END`, no second compaction) and no message content changes.
- [x] 3.3 One assertion in the test that a long non-whitelisted message (e.g. a hotel reply `HumanMessage`/tool reply from `reply_to_hotel`) is preserved verbatim through `cleanup`.

## 4. Verification & deploy

- [x] 4.1 `uv run ruff check && uv run ruff format` clean.
- [x] 4.2 `uv run ty check` clean (src/ only — note: compaction.py is in src/ so must pass the gate).
- [x] 4.3 `uv run pytest tests/test_context_compaction.py -q` green.
- [x] 4.4 `uv run alembic check` — confirm no model/DB drift (no migration expected).
- [x] 4.5 Commit on `main` and deploy: `env -u RAILWAY_TOKEN -u RAILWAY_API_TOKEN railway up --service app --detach -m "feat: context compaction for search/extract tool messages"`, then poll `railway deployment list --service app --json` to `SUCCESS`.
