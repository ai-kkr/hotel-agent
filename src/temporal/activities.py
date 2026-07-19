from pydantic import BaseModel
from temporalio import activity

from src.agent.state import EmailState
from src.context import get_context
from src.db.repositories import ClientRepository
from src.db.session import session_context
from src.logging import get_logger
from src.temporal.model import RunInput


class SaveStateInput(BaseModel):
    client_id: int
    state: EmailState


@activity.defn
async def load_state(client_id: int) -> EmailState | None:
    """Load the persisted agent state for a client, or ``None`` if none is stored yet."""
    ctx = get_context()
    async with session_context(ctx.session_factory) as session:
        return await ClientRepository(session).get_state_by_client_id(client_id=client_id)


@activity.defn
async def save_state(input: SaveStateInput) -> None:
    """Persist the agent state for a client (upsert — ``client_id`` is the ``states`` primary key)."""
    ctx = get_context()
    async with session_context(ctx.session_factory) as session:
        await ClientRepository(session).set_state_by_client_id(
            client_id=input.client_id,
            state=input.state,
        )


@activity.defn
async def enqueue_scheduled_turn(run_input: RunInput) -> None:
    """Deliver a scheduled turn into the client's queue — the activity body of :class:`ScheduledTurn`.

    A Temporal Schedule can only *start* a workflow run, not signal-with-start (the Python SDK's
    ``ScheduleActionStartWorkflow`` has no ``start_signal``), so the schedule starts the trivial
    :class:`ScheduledTurn` workflow, which runs this activity. The activity performs the exact
    signal-with-start that :func:`src.temporal.client.agent_step` does, landing the turn on
    ``queue:{thread_id}`` so it serializes against any concurrent live turn and the agent loads the
    latest persisted ``EmailState``. It reaches Temporal through the process-wide
    :func:`src.context.get_temporal_client` (one connection per worker) rather than connecting per
    fire. Identity is frozen into ``run_input`` at create time — only flat data crosses the boundary.
    """
    from temporalio.common import WorkflowIDReusePolicy

    from src.config import get_settings
    from src.context import get_temporal_client
    from src.temporal.queue import ENQUEUE_SIGNAL, AgentQueue

    client = await get_temporal_client()
    settings = get_settings()
    await client.start_workflow(
        AgentQueue.run,
        id=f"queue:{run_input.thread_id}",
        task_queue=settings.temporal_task_queue,
        # Signal-with-start: append to a running queue, or (re)start it + deliver the signal.
        start_signal=ENQUEUE_SIGNAL,
        start_signal_args=[run_input],
        id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
    )
    # A one-shot schedule (``when``/``in``) has now fired its only action — retire it so it doesn't
    # linger as "active" in the catalog / Temporal. Recurring schedules persist (managed explicitly).
    if run_input.one_shot and run_input.task_key is not None:
        await retire_one_shot(run_input.client_id, run_input.task_key)


async def retire_one_shot(client_id: int, task_key: str) -> None:
    """Fire-side cleanup: delete a fired one-shot's Temporal schedule + catalog row.

    Best-effort — a failure on either side is logged, not raised (the turn was already delivered;
    a lingering row is harmless and reconcileable via temporal-ui).
    """
    from src.context import get_context
    from src.db.repositories import ScheduledTaskRepository
    from src.db.session import session_context
    from src.temporal.schedules import delete as schedule_delete

    log = get_logger(__name__)
    try:
        await schedule_delete(client_id=client_id, task_key=task_key)
    except Exception as exc:  # schedule already gone / transient — don't fail the turn
        log.warning(
            "schedule.retire_temporal_failed",
            client_id=client_id,
            task_key=task_key,
            error=str(exc),
        )
    try:
        async with session_context(get_context().session_factory) as session:
            await ScheduledTaskRepository(session).delete(client_id, task_key)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning(
            "schedule.retire_catalog_failed", client_id=client_id, task_key=task_key, error=str(exc)
        )
