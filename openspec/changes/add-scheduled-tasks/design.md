## Context

Today every agent turn is triggered synchronously by one of two entry points that both funnel into
`agent_step()` ([src/temporal/client.py](src/temporal/client.py)):

```
guest text (Telegram)  ─┐
                         ├──▶ agent_step(update, client, state_update=None)
hotel reply (webhook)  ─┘            │  signal-with-start on queue:{thread_id}
                                     ▼
                          AgentQueue (per-client serializer) ─▶ AgentWorkflow.run_user
                                     │  load_state → graph.ainvoke → save_state
                                     ▼
                          pushes reply to Telegram from activities
```

`agent_step` is already literally "give the agent a turn with this description". So a *scheduled*
task is, conceptually, "call `agent_step` not now, but later / on a cron" — no new execution path is
required. The design problem is purely: **what fires the timer, and how do we CRUD it.**

Constraints that shape the design (see CLAUDE.md):
- `EmailContext` carries only flat data across the workflow↔activity boundary; tools fetch heavy
  deps lazily via `get_context()` ([src/context.py](src/context.py)).
- State is persisted in `StateORM` (JSONB) via `load_state`/`save_state` activities — no LangGraph
  checkpointer.
- Per-client turns are already serialized by `AgentQueue` (`queue:{thread_id}`).
- Agent state mutators return `Command(update=...)`; failures self-correct via
  `SelfCorrectionError` ([src/agent/middleware.py](src/agent/middleware.py)).
- Production deploys to Railway; Temporal server is managed there and already supports Schedules.

## Goals / Non-Goals

**Goals:**
- Let the guest (via the agent) create, list, update, and cancel delayed **and** recurring agent
  turns.
- One-shot ("write to the hotel tomorrow at 9am") and recurring ("check for a reply every Monday")
  in one unified mechanism.
- Persisted across worker restarts and Railway redeploys without a new DB table.
- Reuse the existing per-client serialization so a scheduled firing never races a live guest turn.
- Full CRUD addressable through a human-readable, agent-managed `task_key`.

**Non-Goals:**
- No new DB table / alembic migration (Temporal Schedules are the source of truth).
- No bespoke "timer" workflow.
- No first-party admin UI (temporal-ui already exposes schedule CRUD).
- No cross-client sharing; no calendar/GUI for the guest — interaction stays in the Telegram chat.

## Decisions

### D1. Temporal Schedules, not a hand-rolled timer workflow
**Choice:** implement scheduling with Temporal's first-class Schedules API
(`client.schedules().create / list / update / delete / pause / unpause`).

**Alternatives considered:**
- *Timer workflow* (`AgentWorkflow`-like that `await asyncio.sleep`s then enqueues). Handles the
  one-shot case but needs bespoke logic for recurrence, listing, and lifecycle — and gives no
  admin surface. Rejected: Schedules give all of that for free and unify one-shot + recurring.
- *DB table + APScheduler/cron*. Rejected: re-introduces state we'd have to migrate and operate,
  duplicates what Temporal already does, and doesn't survive a process crash as cleanly.

**Why Schedules fit:** a Schedule's *action* starts a workflow on each fire. **Important correction
discovered during implementation (temporalio 1.30):** `ScheduleActionStartWorkflow` has **no
`start_signal`/`start_signal_args`** — a Schedule action can only *start a fresh workflow run*, it
cannot signal-with-start. Since `AgentQueue.run()` takes no args and only receives turns via its
`add_task` signal (driven by `agent_step`'s signal-with-start), the schedule can't deliver a turn
into the queue directly.

The chosen bridge is a trivial **kicker workflow** `ScheduledTurn` (registered alongside
`AgentQueue`/`AgentWorkflow`) whose single activity `enqueue_scheduled_turn` performs the *same*
signal-with-start `agent_step` does. So the schedule's action is
`ScheduleActionStartWorkflow(ScheduledTurn.run, arg=RunInput, id="kkr-kick:{client_id}:{task_key}")`;
on each fire Temporal starts `ScheduledTurn`, which runs the activity, which signal-with-starts
`queue:{thread_id}`. A firing is therefore indistinguishable from a guest turn: it lands on the
per-client queue, runs as an `AgentWorkflow` child, loads the latest `EmailState`, and serializes
against any concurrent live turn. This was a user-approved deviation from the original D1 (the
"Kicker workflow + activity" option); the rejected alternatives were (a) starting `AgentQueue` with
the turn as a run arg (drops any fire that lands while the queue is mid-drain) and (b) starting
`AgentWorkflow.run_user` directly (bypasses per-client serialization).

```
tool set_scheduled_task (activity)
   │  get_context().temporal_client
   ▼
client.create_schedule(
   id      = "kkr-sched:{client_id}:{task_key}",
   action  = ScheduleActionStartWorkflow(
                 ScheduledTurn.run, arg=RunInput(state=<scheduled turn>, thread_id, client_id,
                                                 telegram_id, client_email, client_inbox, from_email),
                 id="kkr-kick:{client_id}:{task_key}", task_queue=KKR_TEMPORAL_TASK_QUEUE),
   spec    = ScheduleSpec(...)   # calendar (one-shot, remaining_actions=1) or cron (recurring)
   memo    = {client_id, description, created_at, kind, schedule}
)
   ┄ Temporal server stores it ┄
   ┊ at fire time ┊
   ▼
ScheduledTurn.run ──activity──▶ enqueue_scheduled_turn
   │  get_context().temporal_client  (signal-with-start, exactly like agent_step)
   ▼
AgentQueue (queue:{thread_id}) ─▶ AgentWorkflow.run_user ─▶ "scheduled turn" runs like any other
```

The kicker workflow id is fixed per task (`kkr-kick:{client_id}:{task_key}`). The action leaves
`workflow_id_reuse_policy` at the server default (ALLOW_DUPLICATE), so once a fire's sub-second run
completes the closed id is reused on the next fire; the default overlap policy (SKIP) harmlessly
drops a fire only if the previous run is somehow still going.

### D2. Addressing via an agent-supplied `task_key`; deterministic schedule id
**Choice:** every schedule id is `kkr-sched:{client_id}:{task_key}`. `task_key` is a short,
human-readable, agent-chosen slug (`"early-checkin"`, `"weekly-reply-check"`). The agent uses
`task_key` in all CRUD tools; the raw schedule id never appears to the guest.

**Why:**
- **Listing/existence is NOT done via Temporal.** `list_schedules(query=…)` can't filter schedules
  server-side: the visibility list filter (`STARTS_WITH`, search attributes) applies only to
  *Workflow Executions*, schedules have no queryable id/search-attribute, and a memo isn't queryable
  ([community-confirmed](https://community.temporal.io/t/list-temporal-schedules-based-on-search-attributes/10699)).
  So a Temporal listing is a full scan of *every* client's schedules — unacceptable on the hot path
  (every `list` / `update` / `cancel`). Instead the agent keeps a per-client **DB catalog**
  (`scheduled_tasks`, keyed `(client_id, task_key)`) holding the display metadata; `list_scheduled_tasks`
  and existence checks read it. Temporal remains the firing source of truth; the catalog is the index,
  kept in sync on every create/update/cancel (see the "Risks" section for the ordering). The
  `kkr-sched:{client_id}:{task_key}` id still exists for temporal-ui and is still deterministic for
  idempotent creates.
- `task_key` doubles as the human handle the agent renders to the guest in `list_scheduled_tasks`.
- Idempotency: the id is deterministic in `task_key`, so a retried `set_scheduled_task` re-targets
  the same schedule instead of creating a duplicate. "Already exists" is **success**, not an error
  (see D4).

**Rejected:** id-prefix client-side filtering of `list_schedules` (the original D2) — works but is a
full scan on every call, rejected once the listing volume grew; a custom search attribute on
schedules — doesn't work (Temporal can't filter schedules by search attributes); hash-of-(desc+spec)
/ uuid ids (lose idempotency or a human handle).

### D3. The scheduled turn payload
At create time the tool captures the flat identity fields from `EmailContext` into the
`RunInput` (identical to what `agent_step` builds in [src/temporal/client.py](src/temporal/client.py)):
`client_id`, `thread_id`, `telegram_id`, `client_email`, `client_inbox`, `from_email`. The
`RunInput.state` is a minimal `EmailState` whose only meaningful field is
`messages=[HumanMessage("⏰ Запланированная задача: <description>")]`.

- **State at fire time is read fresh** (`load_state` activity), so booking/threading changes since
  scheduling are seen — `description` must not bake in stale state assumptions; the prompt enforces
  this.
- Only identity fields (flat data) are frozen into the Schedule action args — nothing live crosses
  the converter. `RunInput` and `EmailState` already round-trip through
  `message_aware_data_converter` ([src/temporal/converter.py](src/temporal/converter.py)), so **no
  new non-JSON type** is introduced.

### D4. Create is idempotent; "already exists" is success
**Choice:** `set_scheduled_task` is `max_retries=0`. If `kkr-sched:{client_id}:{task_key}` already
exists, the tool treats it as success and returns `"задача уже была запланирована"` rather than
raising.

**Why:** the per-tool retry wrapper ([src/agent/middleware.py](src/agent/middleware.py)) could fire
after a partial success and duplicate. With `max_retries=0` and a deterministic id, the worst case
on a real network blip is one extra call that no-ops on the existing id. Idempotent-peace beats
retry-resilience here, mirroring why `send_wishes_to_hotel` is also `max_retries=0`.

### D5. Update is full-replace; pause folded in (no separate pause/resume tools)
**Choice:** one tool `update_scheduled_task(task_key, description?, schedule?, paused?)` backed by
`client.schedules().update(updater)` — the updater receives the current descriptor and returns the
mutated one. The schedule id stays stable across the update (history preserved). Pause/resume is
`paused=True/False` inside the same call.

**Why:** Temporal's update model is full-replace anyway; surfacing it as one tool keeps the tool
surface small and matches the user's decision to fold pause into update. `update` on a missing
`task_key` raises `SelfCorrectionError("такой задачи нет, актуальный список: …")`.

### D6. Temporal client via `get_context()`, not per-call `Client.connect`
**Choice:** add a lazily-connected `temporal_client` to the process singleton `get_context()`
([src/context.py](src/context.py)) — one `Client.connect(settings.temporal_target, data_converter=…)`
per worker process, reused across all scheduling tools.

**Why:** tools already fetch heavy deps (model, Mailtrap, Tavily, session_factory) this way; the
existing `agent_step` connects a fresh client per call ([src/temporal/client.py:34](src/temporal/client.py#L34)),
which is fine for an HTTP-handler-driven path but wasteful inside hot tool calls. The `data_converter`
must be the same `message_aware_data_converter` so `RunInput` args on the Schedule action round-trip
identically to `agent_step`.

**Rejected:** passing the client through `EmailContext` — violates the flat-data-only rule.

### D7. Schedule spec shape — pydantic model, naive local time, zone selector
**Choice:** ``schedule`` is a strict pydantic model ``ScheduleInput`` (not a bare dict):
- one-shot → ``{"when": "2026-07-22T09:00:00"}`` — a **naive local** datetime (NO timezone offset),
  translated to a ``ScheduleSpec`` with ``calendars=[…]`` + ``remaining_actions=1``.
- recurring → ``{"cron": "0 9 * * 1", "remaining": N?}`` — a 5-field cron (``remaining`` omitted =
  unbounded). ``remaining`` with ``when`` is rejected by the model.

A model validator enforces "exactly one of ``when``/``cron``" and field validators enforce the naive
format and 5-field cron. **Validation failures self-correct**, not crash: the tool-call wrapper
(:func:`run_tool_call`) catches ``pydantic.ValidationError`` and returns a corrective
``ToolMessage`` (a global, sensible rule — bad tool input should guide the agent, not fail the turn).

**Timezones are NOT baked into the time and NOT guessed by the agent.** Time is passed as the guest
gave it (naive local); the zone is an explicit selector argument ``zone: "home" | "trip"``. Both
zones are IANA names set at ``set_booking_info`` time and stored in ``EmailState``
(``home_timezone`` / ``trip_timezone``) — a deliberate ``EmailState`` addition (the earlier "no
state change" line referred to the scheduling-ack path; the tz fields are a normal booking field
like ``hotel_language``). The tool resolves the selector to the IANA zone from state (self-correcting
if that zone isn't set yet) and passes it as ``ScheduleSpec.time_zone_name``, so Temporal evaluates
both one-shot and cron in that zone (DST-aware) — no manual UTC conversion, and the agent never
computes offsets.

**Rejected:** letting the LLM put a tz offset in ``when`` itself (rejected by the validator) — too
easy to get wrong; the two-zone selector keeps the LLM's job to "pick home or trip". ``ScheduleSpec``
in UTC with the agent choosing the offset was the original D7; it was replaced because relying on
the agent for timezone math is unreliable.

### D8. No new graph nodes; tools are self-contained
**Choice:** scheduling tools live in a new `src/agent/tools/scheduling.py`, registered in the
existing `tools` list. They return `Command(update={"messages": [ack(...)]})` (they append only a
`ToolMessage`). `list_scheduled_tasks` returns a plain string result. The only `EmailState` change
is the two timezone fields (D7); no scheduling-specific state is added.

### D9. Relative scheduling (`in`) — zone-independent
**Choice:** `ScheduleInput` has a third arm, `in` (e.g. `"1h"`, `"90m"`, `"2d"`, `"1h30m"`,
d/h/m/s). The tool resolves it to an absolute UTC instant at call time (`now + parse_duration(in)`)
and builds a one-shot UTC calendar with `remaining_actions=1`. `zone` is **not required** for `in`.

**Why:** "напомни через час / послезавтра" doesn't need a timezone at all — it's a delta from now,
which the tool can take itself (`datetime.now()` in the activity). This covers the common relative
case without forcing the guest/agent to pick a zone, and without the agent doing any arithmetic.
`now()` is fine here — the tool is a Temporal activity, its result is checkpointed, and the fire
instant only needs to be correct at create time.

### D10. Current-time awareness via a human-message stamp (cache-safe)
**Choice:** each incoming guest message gets a one-line current-time context prepended at the chat
entry point (`build_now_context` in [src/bot/core.py](src/bot/core.py)): the message's UTC send time
plus the home/trip local times when those zones are set. The zones are read cheaply via
`ClientRepository.get_timezones` (a JSONB `state->>'home_timezone'`/`'trip_timezone'` select — no
full state load, no migration).

**Why it's cache-safe (the key constraint):** the stamp lives **inside the human message**, which is
the request *tail* — never the cached prefix. Injecting "now" into the prefix (e.g. right after the
system prompt) would bust the prefix cache every turn (the original rejected Variant A); putting it
in the tail doesn't. In later turns the stamped message is a stable historical prefix byte-for-byte,
which is correct (it records when that message arrived). The agent uses the stamp to interpret
relative phrasing and to disambiguate home-vs-trip; it never computes offsets itself.

**Home/trip disambiguation** for absolute future times is a prompt rule (D7/D10 context): the agent
compares the target date to `from_date` and **asks** on the arrival day or when trip dates are
unknown — it does not guess the zone.

## Risks / Trade-offs

- **[Temporal Schedule API surface is broad]** → Mitigation: keep a thin internal helper
  (`src/temporal/schedules.py` or similar) that wraps create/list/update/delete and exposes only
  what the four tools need; tools call the helper, never the raw client. Easier to mock in tests.
- **[Schedule `update` race]** → Mitigation: per-client turns serialize through `AgentQueue`, so two
  CRUD ops on the same client's schedules never run concurrently. `update`'s read-modify-write is
  safe within that guarantee.
- **[Guest meant one-shot but agent created recurring → runaway mail to hotel]** → Mitigation:
  prompt rule — confirm with the guest before creating any *recurring* task; default `remaining` to
  a small cap (e.g. 4) for reply-check patterns rather than unbounded.
- **[Schedule fires while worker is redeploying]** → Mitigation: Temporal persists the schedule and
  the missed-trigger policy; acceptable to retry on next worker up. Not worse than any other turn.
- **[Temporal/DB catalog divergence]** (a crash between the Temporal write and the catalog write) →
  Mitigation: ordered writes chosen so the worst case is benign — *create* writes the catalog first,
  then Temporal, rolling the row back on Temporal failure (no orphan firing schedule = no unwanted
  email); *cancel* deletes Temporal first, then the row (worst case: a stale row, never an
  uncancelled firing); *update* changes Temporal first, then the row (worst case: a stale display
  line). temporal-ui remains the reconciliation surface for any rare orphan.
- **[Identity drift]** (client's `telegram_id`/inbox changes between create and fire) → low-likelihood;
  documented; the captured-at-create fields are what's used. Not worth extra plumbing now.
