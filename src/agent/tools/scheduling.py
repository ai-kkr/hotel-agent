"""Scheduled-task tools (CRUD over a guest's Temporal Schedules).

Each tool is a thin layer over :mod:`src.temporal.schedules`; the heavy lifting (Schedule API,
spec translation, the kicker action) lives there. State-mutating tools append only an ack
``ToolMessage`` (no ``EmailState`` schema change beyond the timezone fields) and so return
``Command(update=...)``; ``list_scheduled_tasks`` returns a plain Russian result string.

Identity comes from the runtime :class:`EmailContext` (``client_id``); schedules are strictly
per-client (``kkr-sched:{client_id}:{task_key}``). Times are NAIVE local strings — the zone is
picked explicitly (``home`` | ``trip``) and resolved from the booking state
(``home_timezone`` / ``trip_timezone`` set via ``set_booking_info``).
"""

from datetime import datetime
from typing import Literal

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.logging import get_logger

from ..context import EmailContext
from ..exceptions import SelfCorrectionError
from ..state import EmailState
from .utils import ack

__all__ = [
    "ScheduleInput",
    "cancel_scheduled_task",
    "list_scheduled_tasks",
    "scheduling_tools",
    "set_scheduled_task",
    "update_scheduled_task",
]

log = get_logger(__name__)

#: The two zones a guest can schedule in — resolved from booking state at call time.
Zone = Literal["home", "trip"]


class ScheduleInput(BaseModel):
    """Strict schedule spec for a scheduled task. Set exactly one of ``when`` / ``cron`` / ``in``.

    - ``when``: a NAIVE local datetime (``YYYY-MM-DDTHH:MM:SS``, NO timezone offset) for a one-shot
      task at an absolute time — interpreted in the zone the caller picks separately.
    - ``cron``: a 5-field cron expression (``minute hour day month weekday``) for a recurring task;
      Temporal evaluates it in the picked zone.
    - ``in``: a relative duration from now (``"1h"``, ``"90m"``, ``"2d"``, ``"1h30m"``) for a
      zone-independent one-shot task — use for "in an hour" / "in 2 days" where no zone is needed.
    ``remaining`` bounds a recurring task (only valid with ``cron``).
    """

    model_config = ConfigDict(populate_by_name=True)

    when: str | None = None
    cron: str | None = None
    in_: str | None = Field(default=None, alias="in")
    remaining: int | None = Field(default=None, ge=1, le=10000)

    @model_validator(mode="after")
    def _exactly_one_kind(self) -> "ScheduleInput":
        present = [f for f, v in (("when", self.when), ("cron", self.cron), ("in", self.in_)) if v]
        if len(present) != 1:
            raise SelfCorrectionError(
                "укажи ровно одно из полей schedule: 'when' (разовая), 'cron' (повторяющаяся) "
                "или 'in' (относительно сейчас)"
            )
        if self.remaining is not None and self.cron is None:
            raise SelfCorrectionError("'remaining' имеет смысл только вместе с 'cron'")
        return self

    @field_validator("when")
    @classmethod
    def _naive_local_when(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            dt = datetime.fromisoformat(v)
        except ValueError as e:
            raise SelfCorrectionError(
                f"'when' должен быть в формате 'YYYY-MM-DDTHH:MM:SS': {v!r}"
            ) from e
        if dt.tzinfo is not None:
            raise SelfCorrectionError(
                "'when' — это локальное время БЕЗ часового пояса; зону задаёт отдельный аргумент zone"
            )
        return v

    @field_validator("cron")
    @classmethod
    def _five_field_cron(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v.split()) != 5:
            raise SelfCorrectionError(
                "'cron' должен состоять ровно из 5 полей: minute hour day month weekday"
            )
        return v

    @field_validator("in_")
    @classmethod
    def _valid_duration(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Lazy import avoids a module-load cycle (schedules → activities → db.models).
        from src.temporal.schedules import parse_duration

        try:
            parse_duration(v)
        except ValueError as e:
            # parse_duration raises ValueError on a malformed duration — convert to self-correction
            # so the agent is guided (ToolMessage) instead of the turn crashing on a raw ValueError.
            raise SelfCorrectionError(str(e)) from e
        return v


def _client_id(runtime: ToolRuntime[EmailContext, EmailState]) -> int:
    client_id = runtime.context.get("client_id")
    if not client_id:
        raise SelfCorrectionError(
            "Неизвестен client_id — невозможно адресовать запланированную задачу."
        )
    return client_id


def _resolve_zone(state: EmailState, zone: Zone) -> str:
    """Map the ``home``/``trip`` selector to the IANA zone from booking state, or self-correct.

    Scheduling is impossible before the relevant zone is set via ``set_booking_info``.
    """
    key = "home_timezone" if zone == "home" else "trip_timezone"
    tz = state.get(key)
    if not tz:
        raise SelfCorrectionError(
            f"Часовой пояс для zone={zone!r} не задан. Сначала вызови set_booking_info и укажи "
            f"{key} (IANA-имя, например 'Europe/Moscow')."
        )
    return tz


def _render_list(tasks: list[dict]) -> str:
    if not tasks:
        return "Запланированных задач нет."
    lines = ["Запланированные задачи:"]
    for t in tasks:
        status = "пауза" if t.get("paused") else "активна"
        summary = t.get("spec_summary") or "—"
        remaining = t.get("remaining")
        rem_part = f", осталось {remaining}" if remaining is not None else ""
        desc = t.get("description") or "—"
        lines.append(f"- {t['task_key']} [{status}]: {desc} — {summary}{rem_part}")
    return "\n".join(lines)


def _resolve_zone_for(schedule: ScheduleInput, state: EmailState, zone: Zone | None) -> str | None:
    """Resolve the zone only when the schedule needs it (``when``/``cron``); ``in`` needs none.

    ``in`` (relative to now) is zone-independent, so the guest's "через час" works with no zone set.
    """
    if schedule.in_ is not None:
        return None
    if zone is None:
        raise SelfCorrectionError(
            "для 'when'/'cron' укажи zone ('home' или 'trip'). Для относительного 'in' зона не нужна."
        )
    return _resolve_zone(state, zone)


@tool
async def set_scheduled_task(
    task_key: str,
    description: str,
    schedule: ScheduleInput,
    runtime: ToolRuntime[EmailContext, EmailState],
    zone: Zone | None = None,
):
    """Schedule an agent turn for later (one-shot / relative) or on a recurring basis.

    ``task_key`` is a short, unique, human-readable slug you choose (e.g. "early-checkin",
    "weekly-reply-check"). It identifies the task in every other scheduling tool; the guest never
    sees the raw id. If a task with this ``task_key`` already exists, the call still succeeds and
    reports that the task was already planned (it does NOT overwrite — use update_scheduled_task
    to change it).

    ``description`` is what the future turn is about — written so it still makes sense at fire time,
    because the agent reads the latest booking/state then, not what is true now.

    ``schedule`` carries the timing — exactly one of:
      - ``when``: a NAIVE local datetime ``"YYYY-MM-DDTHH:MM:SS"`` (NO timezone offset) for a
        one-shot task at an absolute time. Fires exactly once.
      - ``cron``: a 5-field cron expression (``minute hour day month weekday``) for a recurring
        task; optionally ``remaining`` to cap the number of firings (omit for unbounded).
      - ``in``: a relative duration (``"1h"``, ``"90m"``, ``"2d"``, ``"1h30m"``) for a one-shot task
        "from now" — NO zone needed, use it for "через час" / "послезавтра".
    ``when``/``cron`` times are interpreted in ``zone`` — Temporal evaluates it there (DST-aware).

    ``zone`` selects which booking timezone the time is expressed in: ``"home"`` (guest's home
    zone, ``home_timezone``) or ``"trip"`` (destination/hotel zone, ``trip_timezone``). Required for
    ``when``/``cron``; not needed for ``in``. The chosen zone must already be set via
    ``set_booking_info``; if it isn't, you'll be told to set it first. Pass the time the guest gave
    as-is and pick the zone — do not compute offsets yourself.

    Only create a recurring task AFTER confirming the plan with the guest, and prefer a bounded
    ``remaining`` for reply-check / polling patterns.

    Args:
        task_key: Short unique slug identifying this task.
        description: What the scheduled turn should accomplish.
        schedule: ``{"when": ...}`` / ``{"cron": ...}`` / ``{"in": ...}``.
        zone: ``"home"`` or ``"trip"`` — required for ``when``/``cron``, ignored for ``in``.
    """
    from src.context import get_context
    from src.db.repositories import ScheduledTaskRepository
    from src.db.session import session_context
    from src.temporal.schedules import (
        create_or_idempotent,
        remaining_of,
        summarize_schedule,
    )

    client_id = _client_id(runtime)
    zone_tz = _resolve_zone_for(schedule, runtime.state, zone)
    log.info(
        "tool.set_scheduled_task", task_key=task_key, schedule=schedule.model_dump(), zone=zone
    )

    summary = summarize_schedule(schedule, zone)
    remaining = remaining_of(schedule)
    # DB catalog first: if the Temporal create then fails, we roll the row back so a crash can't
    # leave an orphan firing schedule (which would send an unwanted email later). Idempotent on
    # task_key either way — a repeated create upserts the same row.
    async with session_context(get_context().session_factory) as session:
        await ScheduledTaskRepository(session).upsert(
            client_id=client_id,
            task_key=task_key,
            description=description,
            spec_summary=summary,
            paused=False,
            remaining=remaining,
        )
    try:
        outcome = await create_or_idempotent(
            client_id=client_id,
            task_key=task_key,
            description=description,
            schedule=schedule,
            zone=zone,
            zone_tz=zone_tz,
            ctx=runtime.context,
        )
    except Exception:
        async with session_context(get_context().session_factory) as session:
            await ScheduledTaskRepository(session).delete(client_id, task_key)
        raise

    content = (
        f"Задача «{task_key}» уже была запланирована ранее."
        if outcome == "exists"
        else f"Задача «{task_key}» запланирована."
    )
    return Command(update={"messages": [ack(runtime, content=content)]})


@tool
async def list_scheduled_tasks(runtime: ToolRuntime[EmailContext, EmailState]):
    """List the guest's scheduled tasks (active and paused).

    Returns a plain Russian summary, one line per task: the ``task_key``, status (active/paused),
    description, schedule summary, and remaining firings (if bounded). Tasks belonging to other
    guests are never shown. Served from the per-client DB catalog — no Temporal scan.
    """
    from src.context import get_context
    from src.db.repositories import ScheduledTaskRepository
    from src.db.session import session_context

    client_id = _client_id(runtime)
    log.info("tool.list_scheduled_tasks", client_id=client_id)
    # Read the catalog rows and snapshot them into plain dicts while the session is open (the ORM
    # objects would be detached after close).
    async with session_context(get_context().session_factory) as session:
        rows = await ScheduledTaskRepository(session).list_by_client(client_id)
        tasks = [
            {
                "task_key": r.task_key,
                "description": r.description,
                "spec_summary": r.spec_summary,
                "paused": r.paused,
                "remaining": r.remaining,
            }
            for r in rows
        ]
    return _render_list(tasks)


@tool
async def update_scheduled_task(
    task_key: str,
    runtime: ToolRuntime[EmailContext, EmailState],
    description: str | None = None,
    schedule: ScheduleInput | None = None,
    zone: Zone | None = None,
    paused: bool | None = None,
):
    """Change a scheduled task — its description, its schedule, and/or its paused state.

    This is a full-replace of whatever you pass (the schedule id stays stable). Any argument you
    omit is left unchanged. ``paused=True`` pauses the task (stops firing until resumed);
    ``paused=False`` resumes it. If ``task_key`` doesn't exist, you'll be told the actual list.

    When you pass a new ``schedule``, also pass ``zone`` if it uses ``when``/``cron`` (the zone the
    new time is in), exactly like in ``set_scheduled_task``. For ``in`` no zone is needed.

    Args:
        task_key: The task to update.
        description: New description (optional).
        schedule: New ``{"when": ...}`` / ``{"cron": ...}`` / ``{"in": ...}`` schedule (optional).
        zone: ``"home"`` or ``"trip"`` — required when ``schedule`` is ``when``/``cron``.
        paused: ``True`` to pause, ``False`` to resume (optional).
    """
    from src.context import get_context
    from src.db.repositories import ScheduledTaskRepository
    from src.db.session import session_context
    from src.temporal.schedules import (
        remaining_of,
        summarize_schedule,
    )
    from src.temporal.schedules import (
        update as schedule_update,
    )

    client_id = _client_id(runtime)
    zone_tz = _resolve_zone_for(schedule, runtime.state, zone) if schedule is not None else None
    log.info(
        "tool.update_scheduled_task",
        task_key=task_key,
        schedule=schedule.model_dump() if schedule else None,
        zone=zone,
        paused=paused,
    )

    # Existence check + snapshot the current display values (for fields the caller omits).
    async with session_context(get_context().session_factory) as session:
        repo = ScheduledTaskRepository(session)
        row = await repo.get(client_id, task_key)
        if row is None:
            keys = await repo.keys_for_client(client_id)
            raise SelfCorrectionError(
                f"Задачи «{task_key}» нет. Актуальный список: {', '.join(keys) or '—'}."
            )
        cur_desc, cur_summary = row.description, row.spec_summary
        cur_paused, cur_remaining = bool(row.paused), row.remaining

    # Temporal first: on failure the catalog row keeps its old (still-correct) values.
    await schedule_update(
        client_id=client_id,
        task_key=task_key,
        ctx=runtime.context,
        description=description,
        schedule=schedule,
        zone=zone,
        zone_tz=zone_tz,
        paused=paused,
    )

    eff_desc = description if description is not None else cur_desc
    eff_paused = bool(paused) if paused is not None else cur_paused
    if schedule is not None:
        eff_summary = summarize_schedule(schedule, zone)
        eff_remaining = remaining_of(schedule)
    else:
        eff_summary, eff_remaining = cur_summary, cur_remaining
    async with session_context(get_context().session_factory) as session:
        await ScheduledTaskRepository(session).upsert(
            client_id=client_id,
            task_key=task_key,
            description=eff_desc,
            spec_summary=eff_summary,
            paused=eff_paused,
            remaining=eff_remaining,
        )

    action = "приостановлена" if paused else ("возобновлена" if paused is False else "обновлена")
    return Command(update={"messages": [ack(runtime, content=f"Задача «{task_key}» {action}.")]})


@tool
async def cancel_scheduled_task(task_key: str, runtime: ToolRuntime[EmailContext, EmailState]):
    """Cancel a scheduled task so it will not fire again.

    Only future firings are removed — a turn that already fired cannot be taken back. If ``task_key``
    doesn't exist, you'll be told the actual list.

    Args:
        task_key: The task to cancel.
    """
    from src.context import get_context
    from src.db.repositories import ScheduledTaskRepository
    from src.db.session import session_context
    from src.temporal.schedules import delete as schedule_delete

    client_id = _client_id(runtime)
    log.info("tool.cancel_scheduled_task", task_key=task_key)

    # Existence check (cheap DB lookup); produce the helpful "actual list" error if absent.
    async with session_context(get_context().session_factory) as session:
        repo = ScheduledTaskRepository(session)
        row = await repo.get(client_id, task_key)
        if row is None:
            keys = await repo.keys_for_client(client_id)
            raise SelfCorrectionError(
                f"Задачи «{task_key}» нет. Актуальный список: {', '.join(keys) or '—'}."
            )

    # Temporal first (stop future firings), then drop the catalog row. A crash between them leaves a
    # stale row at worst — never an uncancelled firing schedule.
    await schedule_delete(client_id=client_id, task_key=task_key)
    async with session_context(get_context().session_factory) as session:
        await ScheduledTaskRepository(session).delete(client_id, task_key)
    return Command(update={"messages": [ack(runtime, content=f"Задача «{task_key}» отменена.")]})


scheduling_tools = [
    set_scheduled_task,
    list_scheduled_tasks,
    update_scheduled_task,
    cancel_scheduled_task,
]
