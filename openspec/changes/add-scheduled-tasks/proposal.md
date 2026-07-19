## Why

The agent currently only acts reactively — it runs a turn when the guest writes in Telegram or a
hotel replies. There is no way for the guest (or the agent itself) to fire a turn later or on a
schedule: "remind the hotel about early check-in three days before arrival", "check once a week
whether the hotel has replied". Scheduling lets the agent carry genuinely autonomous follow-up,
which is the project's whole pitch, instead of being silent until poked.

## What Changes

- Add a new agent capability: **scheduled tasks** — delayed and recurring agent turns driven by
  Temporal Schedules (the firing schedule lives server-side on Temporal; a per-client `scheduled_tasks`
  DB table is the agent's list/existence catalog — see Impact for why).
- New agent tools in `src/agent/tools/` forming a full CRUD over a guest's scheduled tasks:
  - `set_scheduled_task(task_key, description, schedule)` — create (idempotent).
  - `list_scheduled_tasks()` — read, returns per-client list with `next_run` and a spec summary.
  - `update_scheduled_task(task_key, description?, schedule?, paused?)` — update (also pause/resume
    via `paused`; full-replace of spec/action, stable id).
  - `cancel_scheduled_task(task_key)` — delete (cancels future firings only).
- A scheduled firing reuses the existing path: the Schedule's action starts a trivial **kicker
  workflow** `ScheduledTurn`, whose one activity does the same signal-with-start `agent_step` does,
  enqueuing a turn on `queue:{thread_id}`. (Temporal's Python SDK `ScheduleActionStartWorkflow` has
  no `start_signal` — a Schedule can only start a workflow run — so a one-activity kicker bridges
  that; see design D1 for the choice and the alternatives that were rejected.)
- Add a lazily-connected `temporal_client` to the process singleton `get_context()`
  ([src/context.py](src/context.py)) so tools can reach the Temporal Schedule API from inside an
  activity without per-call `Client.connect`.
- New retry policies in `config.yaml` for the four tools (`max_retries=0` on create/update/delete;
  idempotency handled by a deterministic schedule id).
- New section in [src/agent/prompts/system_main.md](src/agent/prompts/system_main.md): the agent
  has scheduling tools, and when a turn arrives as a scheduled task it must act autonomously (the
  guest is not in the loop) and confirm with the guest before creating recurring tasks.
- Integration tests on mocks (Temporal schedule client mocked) for the create/list/update/cancel
  path and the idempotency/SelfCorrection behaviours.

Non-goals:
- No new long-running "timer" workflow (Temporal Schedules chosen over a hand-rolled timer; see
  design.md). The new `scheduled_tasks` table is a *catalog* (list/existence index), not a
  re-implementation of scheduling — Temporal remains the firing source of truth; it exists only
  because `list_schedules` can't filter by client server-side (see design D2).
- No admin UI of our own — temporal-ui already lists/pauses/triggers/deletes schedules.
- No cross-client task sharing — tasks are strictly per-client (keyed by `client_id`).

## Capabilities

### New Capabilities
- `scheduled-tasks`: delayed and recurring agent turns — create/list/update/cancel a guest's
  scheduled tasks via Temporal Schedules, each firing as a normal agent turn through the existing
  per-client queue.

### Modified Capabilities
<!-- openspec/specs/ is empty today; no existing capability requirements change. -->

## Impact

- **Risk areas (per CLAUDE.md):**
  - **Temporal workflow↔activity boundary:** the new tools run as activities and call the Temporal
    Schedule client. They do **not** pass live objects through `EmailContext`; identity fields
    (`client_id`, `thread_id`, `telegram_id`, inbox, email) are captured into the Schedule's action
    args at create time, the same flat-data shape `agent_step` already builds. No new non-JSON type
    crosses the data converter.
  - **Agent state/context serializability:** unchanged. `EmailContext` gains nothing on the hot
    serialization path; the `temporal_client` lives in `get_context()` (process side), not in
    `EmailContext`.
  - **Email threading:** unaffected. A scheduled turn loads the latest persisted `EmailState`
    (including `last_outbound_message_id` / `last_hotel_message_id`), so threading headers stay
    correct; scheduling does not write any new threading field.
- **New tools** in `src/agent/tools/` (likely `scheduling.py`): all state-mutating ones return
  `Command(update={"messages": [ack(...)]})` — they only append a ToolMessage to history (no
  `EmailState` schema change); `list_scheduled_tasks` returns a plain result string.
- **Config:** no new `KKR_*` env var strictly required (Schedule client reuses
  `KKR_TEMPORAL_TARGET` / `KKR_TEMPORAL_TASK_QUEUE`); new `tool_retry` entries in `config.yaml`.
- **Deploy:** ships one new alembic migration (`scheduled_tasks` catalog table). Requires
  `railway up --service app` for the new tools/worker code; the migration runs automatically via the
  image entrypoint's `alembic upgrade head`. The Temporal server already supports Schedules. Dev and
  prod are isolated contours (different bot tokens), so deploying prod needs nothing stopped.
- **Worker registration:** the trivial `ScheduledTurn` workflow and its `enqueue_scheduled_turn`
  activity are registered alongside `AgentQueue`/`AgentWorkflow` ([src/temporal/worker.py](src/temporal/worker.py));
  schedules start `ScheduledTurn`, which enqueues a turn on the existing `AgentQueue`.
