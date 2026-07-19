"""Thin wrapper over the Temporal Schedule API for per-client scheduled agent turns.

Schedules live server-side on Temporal; each schedule's action starts the trivial
:class:`ScheduledTurn` workflow, whose activity does the signal-with-start onto the client's queue —
so a firing is just a normal agent turn. Only the four scheduling tools call this module; they never
touch the raw Temporal client, which keeps the surface small and easy to mock in tests.

Schedule ids are ``kkr-sched:{client_id}:{task_key}``; the agent-facing handle is the human-readable
``task_key``. **Listing / existence is NOT done via Temporal** — ``list_schedules`` can't filter by
client server-side (the visibility list filter only applies to Workflow Executions), so the agent
layer keeps its own DB catalog (:class:`src.db.models.ScheduledTaskORM`). This module only
creates / updates / deletes the schedules and renders the human-readable spec summary that the
catalog row stores. Temporal is the engine (firing); the DB catalog is the index (list/existence).

The ``schedule`` argument is a discriminated union:
- one-shot → ``{"when": "2026-07-22T09:00:00"}`` (naive local; zone picked separately)
- relative → ``{"in": "1h"}`` (zone-independent delta from now)
- recurring → ``{"cron": "0 9 * * 1", "remaining": N?}`` (omit ``remaining`` for unbounded)
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleCalendarSpec,
    ScheduleRange,
    ScheduleSpec,
    ScheduleState,
    ScheduleUpdate,
    ScheduleUpdateInput,
)

from src.config import get_settings
from src.context import get_temporal_client
from src.temporal.model import RunInput
from src.temporal.scheduled_turn import ScheduledTurn

if TYPE_CHECKING:
    from collections.abc import Mapping

    from src.agent.context import EmailContext
    from src.agent.tools.scheduling import ScheduleInput

__all__ = [
    "ScheduleNotFoundError",
    "create_or_idempotent",
    "delete",
    "kind_of",
    "parse_duration",
    "remaining_of",
    "schedule_id",
    "summarize_schedule",
    "update",
]


_DURATION = re.compile(
    r"^\s*(?:(\d+)\s*d)?(?:(\d+)\s*h)?(?:(\d+)\s*m)?(?:(\d+)\s*s)?\s*$", re.IGNORECASE
)


def parse_duration(value: str) -> timedelta:
    """Parse a short relative duration — ``"1h"``, ``"90m"``, ``"2d"``, ``"1h30m"`` (d/h/m/s).

    At least one component is required. Used both to validate ``ScheduleInput.in_`` (agent layer)
    and to resolve a relative task to an absolute fire instant (here). Zone-independent.
    """
    m = _DURATION.match(value)
    if not m or not any(m.groups()):
        raise ValueError(
            f"'in' должен быть относительной длительностью вида '1h', '90m', '2d', '1h30m' (d/h/m/s): {value!r}"
        )
    days, hours, minutes, seconds = (int(x) if x else 0 for x in m.groups())
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def schedule_id(client_id: int, task_key: str) -> str:
    """The Temporal Schedule id for a client's task (``kkr-sched:{client_id}:{task_key}``)."""
    return f"kkr-sched:{client_id}:{task_key}"


def _kicker_workflow_id(client_id: int, task_key: str) -> str:
    return f"kkr-kick:{client_id}:{task_key}"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ScheduleNotFoundError(Exception):
    """Raised by :func:`update`/:func:`delete` when ``task_key`` doesn't exist for the client.

    Defensive only — the tool layer checks the DB catalog first; this fires solely on a Temporal/DB
    divergence. The agent never sees it directly.
    """


def _oneshot_calendar(when_local: datetime) -> ScheduleCalendarSpec:
    """A calendar spec matching one specific local instant (year..second all pinned).

    The spec carries ``time_zone_name`` (the resolved zone), so Temporal interprets these components
    in that zone — DST is resolved at the pinned date. No manual UTC conversion.
    """
    return ScheduleCalendarSpec(
        second=[ScheduleRange(0)],
        minute=[ScheduleRange(when_local.minute)],
        hour=[ScheduleRange(when_local.hour)],
        day_of_month=[ScheduleRange(when_local.day)],
        month=[ScheduleRange(when_local.month)],
        year=[ScheduleRange(when_local.year)],
    )


def _build_spec(schedule: ScheduleInput, zone_tz: str | None) -> ScheduleSpec:
    """Translate the validated :class:`ScheduleInput` to a :class:`ScheduleSpec`.

    - ``when``: naive local time, anchored to ``zone_tz`` (the picked zone) via ``time_zone_name``.
    - ``cron``: 5-field cron, evaluated in ``zone_tz``.
    - ``in_``: relative duration from now — resolved to a UTC instant here (zone-independent), so the
      guest's "через час" works without any zone.
    ``ScheduleInput`` has already validated the shape, so no defensive parsing here.
    """
    if schedule.in_ is not None:
        # Relative — resolve to an absolute UTC instant at call time (this runs in an activity).
        fire_at = datetime.now(UTC) + parse_duration(schedule.in_)
        return ScheduleSpec(calendars=[_oneshot_calendar(fire_at)], time_zone_name="UTC")
    if schedule.when is not None:
        when_local = datetime.fromisoformat(schedule.when)  # naive — validated upstream
        return ScheduleSpec(
            calendars=[_oneshot_calendar(when_local)],
            time_zone_name=zone_tz,
        )
    # ``in_`` and ``when`` are None, so by ScheduleInput's model invariant ``cron`` is set.
    assert schedule.cron is not None
    return ScheduleSpec(cron_expressions=[schedule.cron], time_zone_name=zone_tz)


def _build_state(
    schedule: ScheduleInput | None,
    *,
    paused: bool,
    current: ScheduleState | None,
) -> ScheduleState:
    """Build the schedule state: ``remaining_actions``/``limited_actions`` + paused flag.

    When a ``schedule`` is given, the action cap is derived from it (one-shot — ``when`` or ``in_``
    → 1; recurring with ``remaining`` → N; unbounded recurring → no cap). When omitted (e.g. a
    pause-only update), the current cap is preserved.
    """
    if schedule is not None:
        if schedule.when is not None or schedule.in_ is not None:
            return ScheduleState(paused=paused, limited_actions=True, remaining_actions=1)
        if schedule.remaining is not None:
            return ScheduleState(
                paused=paused, limited_actions=True, remaining_actions=schedule.remaining
            )
        return ScheduleState(paused=paused)
    return ScheduleState(
        paused=paused,
        limited_actions=current.limited_actions if current else False,
        remaining_actions=current.remaining_actions if current else 0,
    )


def kind_of(schedule: ScheduleInput) -> Literal["one-shot", "recurring"]:
    """:literal:`"one-shot"` (``when``/``in``) or :literal:`"recurring"` (``cron``) — for the catalog."""
    return "recurring" if schedule.cron is not None else "one-shot"


def remaining_of(schedule: ScheduleInput) -> int | None:
    """The remaining-firings count to store in the catalog (only a bounded recurring task has one)."""
    if schedule.cron is not None and schedule.remaining is not None:
        return schedule.remaining
    return None


def summarize_schedule(schedule: ScheduleInput, zone: str | None) -> str:
    """Russian, human-readable one-liner for the schedule — stored in the catalog and shown in lists.

    NB: the remaining-firings count is rendered separately (from the catalog's ``remaining`` column),
    so it's deliberately not folded into this summary.
    """
    zone_part = f" ({zone})" if zone else ""
    if schedule.in_ is not None:
        return f"через {schedule.in_}"  # relative — zone-independent
    if schedule.when is not None:
        try:
            dt = datetime.fromisoformat(schedule.when)
            return "разово " + dt.strftime("%d.%m %H:%M") + zone_part
        except ValueError:
            return f"разово {schedule.when}{zone_part}"
    return f"каждый {schedule.cron}{zone_part}"


def _build_run_input(
    client_id: int,
    description: str,
    ctx: EmailContext,
    *,
    task_key: str,
    one_shot: bool,
) -> RunInput:
    """Build the scheduled-turn :class:`RunInput` from the runtime identity, exactly like ``agent_step``.

    ``thread_id`` is derived from ``client_id`` the same way ``ClientORM.thread_id`` computes it, so
    no DB lookup is needed. Only flat identity fields go into the action args (``EmailContext`` is
    unchanged on its serialization path); the turn's only state is the scheduling banner message.
    ``task_key``/``one_shot`` are scheduling metadata so the ``enqueue_scheduled_turn`` activity can
    retire a one-shot after it fires.
    """
    from langchain_core.messages import HumanMessage

    return RunInput(
        client_id=client_id,
        thread_id=f"client:{client_id:04d}",
        telegram_id=ctx.get("telegram_id") or 0,
        state={"messages": [HumanMessage(f"⏰ Запланированная задача: {description}")]},  # type: ignore[typeddict-item]
        from_email=ctx.get("from_email"),
        client_inbox=ctx.get("reply_to"),
        client_email=ctx.get("user_email"),
        task_key=task_key,
        one_shot=one_shot,
    )


def _action_memo(
    *,
    client_id: int,
    description: str,
    schedule: ScheduleInput,
    zone: str | None,
    zone_tz: str | None,
    created_at: str = "",
) -> dict[str, Any]:
    """Metadata on the Temporal action — for temporal-ui visibility (NOT used for listing)."""
    return {
        "client_id": client_id,
        "description": description,
        "kind": kind_of(schedule),
        "zone": zone,
        "zone_tz": zone_tz,
        "summary": summarize_schedule(schedule, zone),
        "created_at": created_at,
        "schedule": schedule.model_dump(by_alias=True),
    }


def _build_action(
    client_id: int,
    task_key: str,
    run_input: RunInput,
    memo: Mapping[str, Any],
) -> ScheduleActionStartWorkflow:
    """The schedule's action: start :class:`ScheduledTurn` with the frozen turn as its arg."""
    return ScheduleActionStartWorkflow(
        ScheduledTurn.run,
        arg=run_input,
        id=_kicker_workflow_id(client_id, task_key),
        task_queue=get_settings().temporal_task_queue,
        memo=memo,
    )


def _memo_of(action: Any) -> dict[str, Any]:
    """Best-effort read of the action memo (used by :func:`update` to preserve current fields)."""
    if isinstance(action, ScheduleActionStartWorkflow) and action.memo:
        return dict(action.memo)
    return {}


async def create_or_idempotent(
    *,
    client_id: int,
    task_key: str,
    description: str,
    schedule: ScheduleInput,
    zone: str | None,
    zone_tz: str | None,
    ctx: EmailContext,
) -> Literal["created", "exists"]:
    """Create the schedule, treating an existing ``task_key`` as success (idempotent).

    The deterministic id means a retried create (``max_retries=0`` still re-targets the same id on a
    second agent call) re-creates nothing. Returns ``"created"`` or ``"exists"`` so the tool can word
    the guest-facing acknowledgement correctly.
    """
    client = await get_temporal_client()
    sched_id = schedule_id(client_id, task_key)
    one_shot = kind_of(schedule) == "one-shot"
    memo = _action_memo(
        client_id=client_id,
        description=description,
        schedule=schedule,
        zone=zone,
        zone_tz=zone_tz,
        created_at=_now_iso(),
    )
    built = Schedule(
        action=_build_action(
            client_id,
            task_key,
            _build_run_input(client_id, description, ctx, task_key=task_key, one_shot=one_shot),
            memo,
        ),
        spec=_build_spec(schedule, zone_tz),
        state=_build_state(schedule, paused=False, current=None),
    )
    try:
        await client.create_schedule(sched_id, built, memo=memo)
    except ScheduleAlreadyRunningError:
        return "exists"
    return "created"


async def update(
    *,
    client_id: int,
    task_key: str,
    ctx: EmailContext,
    description: str | None = None,
    schedule: ScheduleInput | None = None,
    zone: str | None = None,
    zone_tz: str | None = None,
    paused: bool | None = None,
) -> None:
    """Full-replace the schedule's spec/action/state, keeping the id stable; fold pause/resume in.

    ``description``/``schedule``/``paused`` are each optional; an omitted one keeps the current value
    (the action's :class:`RunInput` is rebuilt only when ``description`` changes, since that is what
    it carries). When ``schedule`` is given, ``zone``/``zone_tz`` must accompany it (resolved by the
    tool layer). Raises :class:`ScheduleNotFoundError` on a Temporal/DB divergence only.
    """
    client = await get_temporal_client()
    sched_id = schedule_id(client_id, task_key)
    handle = client.get_schedule_handle(sched_id)

    def updater(inp: ScheduleUpdateInput) -> ScheduleUpdate:
        cur = inp.description.schedule
        cur_memo = _memo_of(cur.action)
        # Rebuild the action (new RunInput) only if the description changed; otherwise reuse it as-is.
        # ``if description is not None`` (not a cached flag) so ty narrows ``description`` to ``str``
        # for the :class:`RunInput` build below.
        if description is not None:
            new_memo = {**cur_memo, "description": description}
            # Effective kind: the new schedule's, else the one already on the action.
            eff_kind = (
                kind_of(schedule)
                if schedule is not None
                else str(cur_memo.get("kind") or "one-shot")
            )
            new_memo["kind"] = eff_kind
            if schedule is not None:
                new_memo["schedule"] = schedule.model_dump(by_alias=True)
                new_memo["summary"] = summarize_schedule(schedule, zone)
                if zone is not None:
                    new_memo["zone"] = zone
                if zone_tz is not None:
                    new_memo["zone_tz"] = zone_tz
            new_action = _build_action(
                client_id,
                task_key,
                _build_run_input(
                    client_id, description, ctx, task_key=task_key, one_shot=eff_kind == "one-shot"
                ),
                new_memo,
            )
        else:
            new_action = cur.action
        eff_spec = _build_spec(schedule, zone_tz) if schedule is not None else cur.spec
        eff_paused = bool(paused) if paused is not None else cur.state.paused
        new_state = _build_state(schedule, paused=eff_paused, current=cur.state)
        return ScheduleUpdate(
            schedule=Schedule(action=new_action, spec=eff_spec, policy=cur.policy, state=new_state)
        )

    try:
        await handle.update(updater)
    except ScheduleAlreadyRunningError as e:  # pragma: no cover - defensive
        raise ScheduleNotFoundError(task_key) from e


async def delete(*, client_id: int, task_key: str) -> None:
    """Delete the schedule (future firings only; a fired turn can't be taken back)."""
    client = await get_temporal_client()
    handle = client.get_schedule_handle(schedule_id(client_id, task_key))
    await handle.delete()
