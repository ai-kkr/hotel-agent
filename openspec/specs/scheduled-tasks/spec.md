# scheduled-tasks Specification

## Purpose

The agent can plan its own future turns — one-shot reminders, recurring polls, and relative-offset
tasks — that fire as Temporal Schedules and re-enter the normal per-client agent queue at the
configured time. The agent's list/existence catalog lives in a per-client DB table
(`scheduled_tasks`); the firing schedule lives on the Temporal server. Times are naive local
strings plus a `home` | `trip` zone resolved from the booking.

## Requirements

### Requirement: Agent can create a one-shot scheduled task
The system SHALL provide an agent tool `set_scheduled_task(task_key, description, schedule, zone)`
that creates a Temporal Schedule which, at the specified time, enqueues exactly one agent turn
carrying `description` as the turn's message. The turn MUST be delivered through the existing
per-client queue (`AgentQueue` via the `enqueue_scheduled_turn` kicker activity's signal-with-start),
so it serializes against any concurrent live turn and loads the latest persisted `EmailState`.

`task_key` is a short human-readable slug chosen by the agent; the underlying schedule id MUST be
`kkr-sched:{client_id}:{task_key}`. `schedule` is a strict pydantic model (`ScheduleInput`); the
time is a NAIVE local datetime (no timezone offset) and `zone` (`"home"` | `"trip"`) selects which
booking timezone interprets it. Communication with the guest is in Russian.

#### Scenario: Guest asks for a one-shot reminder
- **GIVEN** the guest asks the agent to write to the hotel tomorrow at 09:00 local time
- **WHEN** the agent calls `set_scheduled_task(task_key="early-checkin", description="…", schedule={"when": "2026-07-22T09:00:00"}, zone="trip")`
- **THEN** a Temporal Schedule is created with id `kkr-sched:{client_id}:early-checkin` whose action enqueues an agent turn at that time in the trip zone
- **AND** the tool returns a ToolMessage confirming the task and its next fire time, in Russian

#### Scenario: Scheduled firing reuses the normal turn path
- **GIVEN** a one-shot schedule exists for `client_id=42`
- **WHEN** the schedule fires
- **THEN** `AgentQueue` for `queue:{thread_id}` receives a `RunInput` and runs `AgentWorkflow.run_user`
- **AND** the agent turn loads the latest persisted `EmailState` (including current booking and email-threading headers) rather than any state frozen at create time

### Requirement: Scheduled-task times are anchored to booking timezones, not guessed
The system SHALL store two IANA timezones per booking — `home_timezone` (guest's home) and
`trip_timezone` (destination/hotel) — set via `set_booking_info` and held in `EmailState`. A
scheduling tool's `zone` argument (`"home"` | `"trip"`) MUST resolve to the corresponding stored
timezone and be applied as the Temporal `ScheduleSpec.time_zone_name` (so both one-shot `when` and
recurring `cron` are evaluated in that zone, DST-aware). The agent MUST NOT compute timezone offsets
itself. Scheduling before the selected zone is set MUST self-correct (tell the agent to call
`set_booking_info`), not crash.

#### Scenario: Schedule in the trip zone
- **GIVEN** `trip_timezone="Asia/Shanghai"` is set for the booking
- **WHEN** the agent calls `set_scheduled_task(..., schedule={"when": "2026-07-22T09:00:00"}, zone="trip")`
- **THEN** the schedule's spec carries `time_zone_name="Asia/Shanghai"` and fires at 09:00 Shanghai time

#### Scenario: Zone not yet set self-corrects
- **GIVEN** neither `home_timezone` nor `trip_timezone` is set
- **WHEN** the agent calls `set_scheduled_task(..., zone="home")`
- **THEN** the tool raises `SelfCorrectionError` (surfaced as a ToolMessage) telling the agent to set the timezone via `set_booking_info`

### Requirement: Agent can schedule relative to now, with no timezone
The system SHALL allow `schedule` to express a zone-independent relative offset via an `in` field
(e.g. `{"in": "1h"}`, `{"in": "90m"}`, `{"in": "2d"}`, `{"in": "1h30m"}` — d/h/m/s). A relative
task fires exactly once at the create-time "now + offset" (resolved in UTC by the tool); `zone` is
not required and is ignored for `in`. Exactly one of `when` / `cron` / `in` must be present
(`ScheduleInput` model invariant; a violation self-corrects).

#### Scenario: Guest says "in an hour"
- **GIVEN** the guest asks the agent to remind the hotel in one hour
- **WHEN** the agent calls `set_scheduled_task(task_key="ping", description="…", schedule={"in": "1h"})`
- **THEN** a one-shot schedule is created (no `zone` needed), firing at roughly now+1h, with `remaining_actions=1`

### Requirement: The agent is aware of the current time in the client's zones
The system SHALL stamp the client's current time onto each incoming guest message — UTC plus the
home/trip local times when those zones are set — so the agent can interpret relative phrasing
("today", "tomorrow", "in 3 days"). The stamp MUST be placed inside the human message (the request
tail), not in the prompt prefix, so it does not invalidate the LLM prefix cache. The zones are read
cheaply from the persisted state's JSONB without loading the full state.

#### Scenario: Message carries current-time context
- **WHEN** a guest sends a text message and `home_timezone`/`trip_timezone` are set
- **THEN** the human message enqueued to the agent begins with a `[текущее время клиента — UTC … | дом (…) … | поездка (…) …]` line
- **AND** when no zones are set, only the UTC time is shown

### Requirement: Agent disambiguates home vs trip for absolute future times
The system SHALL instruct the agent (via the system prompt) not to guess the zone when the guest
requests a task at an absolute future time on or around the trip dates: the agent compares the
target date to the booking's `from_date` (before → home, after → trip) and, when the target is the
arrival day or trip dates are unknown, asks the guest (e.g. flight/arrival time) before creating the
task, using the current-time context and booking dates.

#### Scenario: Arrival-day reminder is clarified
- **GIVEN** the trip starts on `from_date=2026-07-22` and the guest asks to "remind tomorrow at 9", where tomorrow is the 22nd
- **WHEN** the agent prepares the create call
- **THEN** the agent asks the guest whether tomorrow is still home or already trip (and the flight/arrival time if relevant) before choosing `zone` and creating the task

### Requirement: Invalid schedule input self-corrects
The system SHALL surface a `schedule` that fails `ScheduleInput` validation (e.g. two of
`when`/`cron`/`in`, a `when` with a timezone offset, a non-5-field `cron`, or a malformed `in`) as a
corrective `ToolMessage` via the tool-call wrapper, not a crash.

#### Scenario: Malformed schedule becomes a ToolMessage
- **WHEN** the agent calls `set_scheduled_task(..., schedule={"when": "2026-07-22T09:00:00+03:00"}, zone="trip")` (offset forbidden)
- **THEN** the tool-call wrapper returns a `ToolMessage` describing the validation error, and the turn continues

### Requirement: Agent can create a recurring scheduled task
The system SHALL allow `schedule` to express recurrence via a `cron` field (5-field, evaluated in the
selected `zone`), optionally bounded by a `remaining` count. The agent MUST confirm with the guest
before creating a recurring task, and the tool SHOULD default reply-check / polling patterns to a
small bounded `remaining` rather than unbounded recurrence.

#### Scenario: Guest asks for a weekly reply check
- **GIVEN** the guest wants the agent to check for a hotel reply every Monday at 09:00
- **WHEN** the agent confirms and calls `set_scheduled_task(task_key="weekly-reply-check", description="…", schedule={"cron": "0 9 * * 1", "remaining": 4}, zone="trip")`
- **THEN** a recurring Temporal Schedule is created with `remaining_actions=4`, evaluated in the trip zone
- **AND** the agent, before calling the tool, asked the guest to confirm the recurring plan (per the prompt rule)

#### Scenario: Unbounded recurrence requires explicit confirmation
- **GIVEN** the guest asks for an open-ended recurring task without a stated end
- **WHEN** the agent prepares the create call
- **THEN** the agent MUST surface the unbounded nature to the guest and obtain confirmation before creating

### Requirement: Create is idempotent on task_key
The create tool MUST be idempotent: calling `set_scheduled_task` with a `task_key` that already
exists for this client MUST succeed (not error) and inform the agent that the task was already
planned. The tool's retry policy MUST be `max_retries=0` so a retried call cannot create a duplicate.

#### Scenario: Duplicate task_key on retry
- **GIVEN** `kkr-sched:{client_id}:early-checkin` already exists
- **WHEN** the create tool is invoked again with the same `task_key`
- **THEN** the tool returns a success ToolMessage stating the task is already planned
- **AND** no second schedule is created

### Requirement: Agent can list scheduled tasks
The system SHALL serve `list_scheduled_tasks()` from a per-client DB catalog
(`scheduled_tasks`, keyed on `(client_id, task_key)`) — NOT by scanning Temporal. (Temporal's
`list_schedules` can't filter schedules server-side: the visibility list filter only applies to
Workflow Executions, and schedules have no queryable id/search attribute, so a Temporal listing is a
full scan of every client's schedules.) The catalog row stores the display metadata; the result MUST
be human-readable in Russian and include, per task: the `task_key`, the `description`, the status
(active/paused), a spec summary ("разово 22.07 09:00 (trip)" / "каждый 0 9 * * 1 (trip)"), and the
remaining-firings count when bounded.

#### Scenario: Guest asks what is scheduled
- **GIVEN** the client has two active schedules and one paused
- **WHEN** the agent calls `list_scheduled_tasks()`
- **THEN** the tool returns all three with their `task_key`, description, status, and spec summary
- **AND** the result excludes any tasks belonging to other clients (the catalog is per-client)

#### Scenario: No scheduled tasks
- **GIVEN** the client has no schedules
- **WHEN** the agent calls `list_scheduled_tasks()`
- **THEN** the tool returns a message stating there are no scheduled tasks

### Requirement: Agent can update a scheduled task
The system SHALL provide `update_scheduled_task(task_key, description?, schedule?, paused?)` that
performs a full-replace of the schedule's spec and action while keeping the schedule id stable. It
MUST support pausing and resuming via `paused=True` / `paused=False`. Operating on a `task_key` that
does not exist for this client MUST raise `SelfCorrectionError`, which the tool-call wrapper surfaces
as a corrective ToolMessage (the agent never crashes and is told the actual list).

#### Scenario: Reschedule a one-shot task
- **GIVEN** `kkr-sched:{client_id}:early-checkin` is set for 22.07 09:00
- **WHEN** the agent calls `update_scheduled_task(task_key="early-checkin", schedule={"when": "2026-07-23T10:00:00+03:00"})`
- **THEN** the schedule's fire time is changed to 23.07 10:00 with the same id and description

#### Scenario: Pause via update
- **GIVEN** an active recurring schedule
- **WHEN** the agent calls `update_scheduled_task(task_key="weekly-reply-check", paused=True)`
- **THEN** the schedule enters the paused state and stops firing until resumed

#### Scenario: Update a missing task
- **GIVEN** no schedule with `task_key="nope"` for this client
- **WHEN** the agent calls `update_scheduled_task(task_key="nope", …)`
- **THEN** the tool raises `SelfCorrectionError` listing the client's actual `task_key`s
- **AND** the wrapper converts it to a ToolMessage hint so the turn continues instead of crashing

### Requirement: Agent can cancel a scheduled task
The system SHALL provide `cancel_scheduled_task(task_key)` that deletes the schedule, removing only
**future** firings (a turn that already fired cannot be taken back). Operating on a missing `task_key`
MUST raise `SelfCorrectionError`.

#### Scenario: Cancel a future task
- **GIVEN** an active schedule for `task_key="early-checkin"`
- **WHEN** the agent calls `cancel_scheduled_task(task_key="early-checkin")`
- **THEN** the schedule is deleted and will not fire
- **AND** the tool returns a confirmation in Russian

#### Scenario: Cancel a missing task
- **GIVEN** no schedule with the given `task_key`
- **WHEN** the agent calls `cancel_scheduled_task(task_key="nope")`
- **THEN** the tool raises `SelfCorrectionError` with the actual list, surfaced as a ToolMessage

### Requirement: `/new` cancels all of a client's scheduled tasks
The system SHALL cancel every scheduled task belonging to a client when their conversation memory
is reset (`/new`), so a clean slate has no pending task firing into the now-empty context. This
deletes each of the client's Temporal schedules and their `scheduled_tasks` catalog rows
(best-effort: a transient Temporal failure skips that task and leaves its catalog row tracked); it
MUST NOT touch other clients' tasks.

#### Scenario: `/new` wipes the client's tasks only
- **GIVEN** client 42 has two scheduled tasks and client 99 has one
- **WHEN** client 42 runs `/new`
- **THEN** both of client 42's schedules and catalog rows are gone
- **AND** client 99's task is untouched

### Requirement: A one-shot task retires after firing
The system SHALL retire a one-shot task (`when` / `in`) once it has fired — deleting its Temporal
schedule and its `scheduled_tasks` catalog row — so a fired reminder does not linger as "active".
The cleanup runs from the `enqueue_scheduled_turn` activity right after the turn is delivered, and
is best-effort (a failure is logged, not raised — the turn was already delivered). Recurring tasks
(`cron`) are NOT auto-retired (they keep firing until explicitly cancelled/updated).

#### Scenario: One-shot disappears after firing
- **GIVEN** a one-shot task `task_key="ping"` (`schedule={"in": "5m"}`)
- **WHEN** the schedule fires and the turn is delivered
- **THEN** the Temporal schedule and the catalog row for `ping` are deleted
- **AND** `list_scheduled_tasks()` no longer shows `ping`

### Requirement: Scheduled tasks survive restarts and redeploys
The firing schedule MUST be persisted by the Temporal server (not in process memory), so worker
restarts and Railway redeploys do not lose or duplicate firings. The DB catalog
(`scheduled_tasks`) is the agent's list/existence index; it introduces a new alembic migration and
table but does NOT alter `states` or add a LangGraph checkpointer.

#### Scenario: Worker restarts between create and fire
- **GIVEN** a one-shot schedule was created
- **WHEN** the worker process restarts before the fire time
- **THEN** the schedule still fires at the originally configured time after the worker is back up

### Requirement: DB catalog stays in sync with Temporal
The system SHALL keep the `scheduled_tasks` DB catalog in sync with Temporal on every create / update
/ cancel. Create writes the catalog row first then the Temporal schedule (rolling the row back on
Temporal failure, so a crash can't leave an orphan firing schedule); cancel deletes the Temporal
schedule first then the row (a crash between them leaves at worst a stale row, never an uncancelled
firing); update changes Temporal first then the row. Existence checks and the "actual list" error
message MUST come from the catalog, not a Temporal scan.

#### Scenario: Create then list reflects the task
- **GIVEN** the agent creates a task for `client_id=42`
- **WHEN** the agent then calls `list_scheduled_tasks()`
- **THEN** the task appears (the catalog row was written alongside the Temporal schedule)

### Requirement: Scheduling tools obey the serialization and serializability constraints
Scheduling tools MUST run as Temporal activities and MUST reach the Temporal Schedule client lazily
via the process singleton `get_context()` (a lazily-connected `temporal_client` reusing
`message_aware_data_converter`). They MUST NOT pass any live object through `EmailContext`. The
Schedule's action args MUST be the same flat `RunInput` shape `agent_step` builds, so no new non-JSON
field crosses the data converter.

#### Scenario: Tool reaches Temporal via get_context
- **WHEN** any scheduling tool runs
- **THEN** it obtains the Temporal client from `get_context().temporal_client` rather than from `EmailContext` or a per-call `Client.connect`

#### Scenario: No live objects cross the boundary
- **WHEN** a schedule is created
- **THEN** only flat identity fields (`client_id`, `thread_id`, `telegram_id`, `client_email`, `client_inbox`, `from_email`) and a minimal `EmailState` are placed in the action's `RunInput`
- **AND** `EmailContext` is unchanged on its serialization path
