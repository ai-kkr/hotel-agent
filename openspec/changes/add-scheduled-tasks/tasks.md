## 1. Temporal Schedule helper

- [x] 1.1 Add a lazily-connected `temporal_client` to `get_context()` ([src/context.py](src/context.py)): one `Client.connect(settings.temporal_target, data_converter=message_aware_data_converter)` per worker process, reusing `message_aware_data_converter` ([src/temporal/converter.py](src/temporal/converter.py)).
- [x] 1.2 Create `src/temporal/schedules.py` — a thin internal wrapper exposing only `create_or_idempotent(task_key, description, schedule, ctx)`, `list_for_client(client_id)`, `update(task_key, client_id, …)`, `delete(task_key, client_id)`; ids `kkr-sched:{client_id}:{task_key}`; memo `{client_id, description, created_at, kind}`. Translate the `schedule` union (`{when}` one-shot / `{cron, remaining?}` recurring) to the right `ScheduleSpec` + `ScheduleActionStartWorkflow(AgentQueue.run, start_signal=ENQUEUE_SIGNAL, start_signal_args=[RunInput])`.
- [x] 1.3 Build the scheduled-turn `RunInput` from `EmailContext` identity fields exactly like [src/temporal/client.py](src/temporal/client.py) `agent_step`, with `state.messages=[HumanMessage("⏅ Запланированная задача: <description>")]` and no other state.

## 2. Agent tools (CRUD)

- [x] 2.1 Create `src/agent/tools/scheduling.py` with `set_scheduled_task(task_key, description, schedule, runtime)` — create idempotently; "already exists" → success ToolMessage.
- [x] 2.2 Add `list_scheduled_tasks(runtime)` — returns a plain Russian string listing tasks with `task_key`, description, status, next run, spec summary.
- [x] 2.3 Add `update_scheduled_task(task_key, description?, schedule?, paused?, runtime)` — full-replace via the helper; `paused` toggles pause/resume; missing `task_key` → `SelfCorrectionError` listing actual keys.
- [x] 2.4 Add `cancel_scheduled_task(task_key, runtime)` — delete; missing `task_key` → `SelfCorrectionError`.
- [x] 2.5 Register all four tools in the `tools` list ([src/agent/tools/__init__.py](src/agent/tools/__init__.py)); state-mutating tools return `Command(update={"messages": [ack(runtime)]})`.

## 3. Prompt + config

- [x] 3.1 Add a "Планирование задач" section to [src/agent/prompts/system_main.md](src/agent/prompts/system_main.md): the four tools exist; the guest-facing language is Russian; convert natural-language timing to ISO 8601 with tz (one-shot) or cron (recurring); act autonomously on a scheduled turn (guest is not in the loop); confirm with the guest before creating any recurring task; default reply-check patterns to a bounded `remaining`.
- [x] 3.2 Add `tool_retry` entries for the four scheduling tools in `config.yaml`: `set_scheduled_task`, `update_scheduled_task`, `cancel_scheduled_task` → `max_retries=0`; `list_scheduled_tasks` → default transient retry (read-only, idempotent).

## 4. Tests (integration-flavored, on mocks)

- [x] 4.1 Add a fake/mock Temporal schedule client (in-memory store keyed by schedule id) usable from tests.
- [x] 4.2 Test the create + idempotent-recreate path end-to-end through the tool (one real `set_scheduled_task` call, then a duplicate `task_key` → success, no second schedule created).
- [x] 4.3 Test `list_scheduled_tasks` returns only the calling client's schedules (prefix + memo filter), including a paused one.
- [x] 4.4 Test `update_scheduled_task` reschedule + pause, and that updating/cancelling a missing `task_key` raises `SelfCorrectionError` (assert it surfaces as a ToolMessage, not a crash).

## 5. Verification

- [x] 5.1 `uv run ruff check && uv run ruff format` — clean on all changed files (pre-existing RUF001/UP017 in untouched files stem from the newer ruff 0.15.20 vs the repo's pinned format).
- [x] 5.2 `uv run ty check` (src/ only) — clean on all new/changed files.
- [x] 5.3 `uv run alembic check` — adds one migration (`scheduled_tasks` catalog); `alembic upgrade head` applies cleanly. Only the repo-wide pre-existing `created_at`/`updated_at` NOT-NULL cosmetic drift remains (same kind on every table).
- [x] 5.4 `uv run pytest` for the new scheduling tests — 5 passed.
- [ ] 5.2–5.4 green on `main`; then deploy with `railway up --service app --detach -m "feat: scheduled tasks (CRUD via Temporal Schedules)"`. (Dev and prod are isolated contours with different bot tokens — no instance needs stopping; migrations run via the image entrypoint's `alembic upgrade head`.)
