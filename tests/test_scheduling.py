"""Integration tests for the scheduled-task tools (CRUD over Temporal Schedules + DB catalog).

The Temporal Schedule *client* is mocked (an in-memory store), but everything else is real: the
four tools, the :mod:`src.temporal.schedules` wrapper (spec translation, id rules, memo), the DB
catalog (:class:`ScheduledTaskORM` on an in-memory SQLite DB), and the per-tool retry/self-correction
wrapper. Listing/existence is served from the DB catalog (Temporal can't filter schedules
server-side); create/update/delete keep both in sync.
"""

import types

import pytest
from langchain_core.messages import ToolMessage
from src.agent.context import EmailContext
from src.agent.exceptions import SelfCorrectionError
from src.agent.middleware import run_tool_call
from src.agent.tools.scheduling import (
    ScheduleInput,
    cancel_scheduled_task,
    list_scheduled_tasks,
    set_scheduled_task,
    update_scheduled_task,
)
from src.config import ToolRetryConfig, ToolRetryPolicy
from src.context import ApplicationContext, set_context
from src.db.session import create_schema, session_factory
from temporalio.client import ScheduleAlreadyRunningError

# --- Fake Temporal schedule client (in-memory store keyed by schedule id) -----------


class _FakeHandle:
    def __init__(self, store: dict, schedule_id: str) -> None:
        self._store = store
        self._id = schedule_id

    async def update(self, updater) -> None:
        schedule, memo = self._store[self._id]
        inp = types.SimpleNamespace(
            description=types.SimpleNamespace(schedule=schedule, id=self._id)
        )
        result = updater(inp)
        result = await result if hasattr(result, "__await__") else result  # sync or async updater
        self._store[self._id] = (result.schedule, memo)

    async def delete(self, **_: object) -> None:
        self._store.pop(self._id, None)


class FakeScheduleClient:
    """Minimal stand-in for the Temporal client's schedule surface (create / handle.update / delete).

    The tools no longer list via Temporal — listing/existence is served from the DB catalog — so the
    fake only needs the create + handle paths the wrapper actually calls.
    """

    def __init__(self) -> None:
        self.store: dict[str, tuple] = {}  # id -> (Schedule, memo)

    async def create_schedule(self, schedule_id, schedule, *, memo=None, **_: object) -> None:
        if schedule_id in self.store:
            raise ScheduleAlreadyRunningError()
        self.store[schedule_id] = (schedule, dict(memo or {}))

    def get_schedule_handle(self, schedule_id: str) -> _FakeHandle:
        return _FakeHandle(self.store, schedule_id)


# --- Fixtures -------------------------------------------------------------------------


@pytest.fixture
async def fake_client():
    """Real in-memory SQLite catalog + a fake Temporal client, wired into the app context."""
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await create_schema(engine)
    client = FakeScheduleClient()
    set_context(
        ApplicationContext(
            bot=None,  # type: ignore[arg-type]
            mailtrap_client=None,  # type: ignore[arg-type]
            session_factory=session_factory(engine),
            tavily_client=None,  # type: ignore[arg-type]
            flight_client=None,  # type: ignore[arg-type]
            temporal_client=client,
        )
    )
    yield client
    await engine.dispose()


def _runtime(client_id: int) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        context=EmailContext(
            client_id=client_id,
            telegram_id=1000 + client_id,
            from_email="bot@sending-domain.example",
            reply_to=f"inbox{client_id}@inbox.example",
            user_email=f"guest{client_id}@example.com",
        ),
        tool_call_id="call-test",
        # Booking state with both scheduling zones set (home = Moscow, trip = Shanghai).
        state={"home_timezone": "Europe/Moscow", "trip_timezone": "Asia/Shanghai"},
    )


_ONESHOT = ScheduleInput(when="2026-07-22T09:00:00")
_RECURRING = ScheduleInput(cron="0 9 * * 1", remaining=4)


# --- Tests ----------------------------------------------------------------------------


async def test_create_then_idempotent_recreate(fake_client: FakeScheduleClient):
    """4.2: one real create, then a duplicate task_key → success, no second schedule."""
    runtime = _runtime(42)

    first = await set_scheduled_task.coroutine(
        task_key="early-checkin",
        description="Напомнить отелю про ранний заезд",
        schedule=_ONESHOT,
        zone="trip",
        runtime=runtime,
    )
    assert "запланирована" in first.update["messages"][0].content
    assert "kkr-sched:42:early-checkin" in fake_client.store
    assert len(fake_client.store) == 1

    second = await set_scheduled_task.coroutine(
        task_key="early-checkin",
        description="Напомнить отелю про ранний заезд",
        schedule=_ONESHOT,
        zone="trip",
        runtime=runtime,
    )
    # Idempotent: reported as already-planned, still exactly one schedule.
    assert "уже была запланирована" in second.update["messages"][0].content
    assert len(fake_client.store) == 1


async def test_list_filters_to_calling_client_including_paused(fake_client: FakeScheduleClient):
    """4.3: list returns only the calling client's tasks (prefix + memo), including a paused one."""
    await set_scheduled_task.coroutine(
        task_key="a", description="задача A", schedule=_ONESHOT, zone="home", runtime=_runtime(42)
    )
    await set_scheduled_task.coroutine(
        task_key="weekly",
        description="проверка ответа",
        schedule=_RECURRING,
        zone="trip",
        runtime=_runtime(42),
    )
    # A different client's task must NOT appear.
    await set_scheduled_task.coroutine(
        task_key="other", description="чужая", schedule=_ONESHOT, zone="home", runtime=_runtime(99)
    )
    # Pause the recurring one via update.
    await update_scheduled_task.coroutine(task_key="weekly", paused=True, runtime=_runtime(42))

    listing = await list_scheduled_tasks.coroutine(runtime=_runtime(42))
    assert "a" in listing
    assert "weekly" in listing
    assert "other" not in listing  # cross-client isolation
    assert "пауза" in listing  # paused state rendered


async def test_update_reschedules_and_pauses(fake_client: FakeScheduleClient):
    """4.4a: update reschedules a one-shot and pauses it; id stays stable."""
    runtime = _runtime(42)
    await set_scheduled_task.coroutine(
        task_key="early", description="d", schedule=_ONESHOT, zone="trip", runtime=runtime
    )

    await update_scheduled_task.coroutine(
        task_key="early",
        schedule=ScheduleInput(when="2026-07-23T10:00:00"),
        zone="trip",
        runtime=runtime,
    )
    paused = await update_scheduled_task.coroutine(task_key="early", paused=True, runtime=runtime)
    assert "приостановлена" in paused.update["messages"][0].content

    listing = await list_scheduled_tasks.coroutine(runtime=runtime)
    assert "пауза" in listing
    # Still a single schedule (update is full-replace on the stable id, not a new one).
    assert len(fake_client.store) == 1


async def test_cancel_removes_task(fake_client: FakeScheduleClient):
    runtime = _runtime(42)
    await set_scheduled_task.coroutine(
        task_key="early", description="d", schedule=_ONESHOT, zone="trip", runtime=runtime
    )
    cancelled = await cancel_scheduled_task.coroutine(task_key="early", runtime=runtime)
    assert "отменена" in cancelled.update["messages"][0].content
    assert fake_client.store == {}


async def test_missing_task_key_surfaces_as_tool_message_not_crash(fake_client: FakeScheduleClient):
    """4.4b: updating/cancelling a missing task_key raises SelfCorrectionError, which the wrapper
    turns into a ToolMessage so the turn continues instead of crashing."""
    runtime = _runtime(42)

    # The tool itself raises SelfCorrectionError (the precondition signal):
    with pytest.raises(SelfCorrectionError):
        await update_scheduled_task.coroutine(task_key="nope", paused=True, runtime=runtime)
    with pytest.raises(SelfCorrectionError):
        await cancel_scheduled_task.coroutine(task_key="nope", runtime=runtime)

    # And the run_tool_call wrapper converts that into a corrective ToolMessage:
    request = types.SimpleNamespace(
        tool_call={
            "id": "c1",
            "name": "update_scheduled_task",
            "args": {"task_key": "nope", "paused": True},
        }
    )

    # executor mirrors what ToolNode does: invoke the tool with the parsed args + runtime.
    async def execute(req):
        return await update_scheduled_task.coroutine(**req.tool_call["args"], runtime=runtime)

    result = await run_tool_call(
        request,  # type: ignore[arg-type]
        execute,
        config=ToolRetryConfig(default=ToolRetryPolicy(max_retries=0)),
    )
    assert isinstance(result, ToolMessage)
    assert "SelfCorrectionError" in result.content


async def test_missing_timezone_self_corrects(fake_client: FakeScheduleClient):
    """Scheduling before the relevant zone is set self-corrects (tells the agent to set it)."""
    runtime = _runtime(42)
    runtime.state = {"home_timezone": "Europe/Moscow"}  # trip_timezone absent
    with pytest.raises(SelfCorrectionError):
        await set_scheduled_task.coroutine(
            task_key="x", description="d", schedule=_ONESHOT, zone="trip", runtime=runtime
        )


async def test_bad_schedule_surfaces_as_tool_message(fake_client: FakeScheduleClient):
    """A malformed schedule raises SelfCorrectionError → a corrective ToolMessage, not a crash."""
    request = types.SimpleNamespace(
        tool_call={
            "id": "c2",
            "name": "set_scheduled_task",
            "args": {
                "schedule": {"when": "2026-07-22T09:00:00+03:00"},
                "zone": "trip",
            },  # offset forbidden
        }
    )

    async def execute(req):
        # Mirrors langchain parsing `schedule` into ScheduleInput; the tz offset is invalid → raises.
        ScheduleInput(**req.tool_call["args"]["schedule"])
        return None

    result = await run_tool_call(
        request,  # type: ignore[arg-type]
        execute,
        config=ToolRetryConfig(default=ToolRetryPolicy(max_retries=0)),
    )
    assert isinstance(result, ToolMessage)
    assert "SelfCorrectionError" in result.content


async def test_relative_in_creates_zoneless_one_shot(fake_client: FakeScheduleClient):
    """`schedule={"in": "1h"}` creates a one-shot UTC schedule with no zone required."""
    runtime = _runtime(42)
    res = await set_scheduled_task.coroutine(
        task_key="soon",
        description="пинг через час",
        schedule=ScheduleInput.model_validate({"in": "1h"}),
        runtime=runtime,  # no zone passed
    )
    assert "запланирована" in res.update["messages"][0].content
    assert "kkr-sched:42:soon" in fake_client.store
    sched, _memo = fake_client.store["kkr-sched:42:soon"]
    # Relative → one-shot UTC calendar, single fire.
    assert sched.state.limited_actions is True
    assert sched.state.remaining_actions == 1
    assert sched.spec.time_zone_name == "UTC"
    assert sched.spec.calendars  # a pinned calendar, not cron


def test_schedule_input_rejects_two_kinds():
    """Invalid ScheduleInput raises SelfCorrectionError (→ corrective ToolMessage, not a crash)."""
    with pytest.raises(SelfCorrectionError):
        ScheduleInput.model_validate({"when": "2026-07-22T09:00:00", "in": "1h"})
    with pytest.raises(SelfCorrectionError):
        ScheduleInput(when="2026-07-22T09:00:00", cron="0 9 * * 1")
    with pytest.raises(SelfCorrectionError):
        ScheduleInput.model_validate({"in": "not-a-duration"})


async def test_cancel_all_scheduled_tasks(fake_client: FakeScheduleClient):
    """`/new`'s cancel-all wipes this client's tasks (Temporal + catalog) and leaves others alone."""
    from src.bot.core import cancel_all_scheduled_tasks

    # Two tasks for client 42, one for client 99.
    await set_scheduled_task.coroutine(
        task_key="a", description="da", schedule=_ONESHOT, zone="home", runtime=_runtime(42)
    )
    await set_scheduled_task.coroutine(
        task_key="b", description="db", schedule=_RECURRING, zone="trip", runtime=_runtime(42)
    )
    await set_scheduled_task.coroutine(
        task_key="other", description="dc", schedule=_ONESHOT, zone="home", runtime=_runtime(99)
    )
    assert len([sid for sid in fake_client.store if sid.startswith("kkr-sched:42:")]) == 2

    cancelled = await cancel_all_scheduled_tasks(42)
    assert cancelled == 2
    # Client 42's schedules gone from Temporal; client 99's intact.
    assert not any(sid.startswith("kkr-sched:42:") for sid in fake_client.store)
    assert "kkr-sched:99:other" in fake_client.store
    # Catalog reflects the same: client 42 empty, client 99 still listed.
    listing42 = await list_scheduled_tasks.coroutine(runtime=_runtime(42))
    listing99 = await list_scheduled_tasks.coroutine(runtime=_runtime(99))
    assert "нет" in listing42
    assert "other" in listing99


async def test_one_shot_retires_after_firing(fake_client: FakeScheduleClient):
    """A fired one-shot is retired (Temporal schedule + catalog row deleted) — no lingering "active"."""
    from src.temporal.activities import retire_one_shot

    await set_scheduled_task.coroutine(
        task_key="ping", description="через 5 минут", schedule=_ONESHOT, zone="trip",
        runtime=_runtime(42),
    )
    assert "kkr-sched:42:ping" in fake_client.store
    assert "ping" in await list_scheduled_tasks.coroutine(runtime=_runtime(42))

    # Fire-side cleanup runs from the enqueue activity after the turn is delivered.
    await retire_one_shot(42, "ping")

    assert "kkr-sched:42:ping" not in fake_client.store
    listing = await list_scheduled_tasks.coroutine(runtime=_runtime(42))
    assert "нет" in listing  # catalog row gone too → not "active" anymore
