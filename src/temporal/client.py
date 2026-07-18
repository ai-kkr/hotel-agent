from temporalio import workflow
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

from src.agent.state import EmailState
from src.config import get_settings
from src.db.models import ClientORM
from src.temporal.model import RunInput
from src.temporal.queue import ENQUEUE_SIGNAL, AgentQueue

with workflow.unsafe.imports_passed_through():
    from src.temporal.converter import message_aware_data_converter


async def agent_step(
    update: EmailState,
    client: ClientORM,
    *,
    state_update: EmailState | None = None,
) -> None:
    """Enqueue an agent turn on the client's per-thread queue via signal-with-start.

    If ``AgentQueue`` for this client is already running, ``add_task`` appends to its deque;
    otherwise the workflow is (re)started and the task is delivered as the first signal. This is
    atomic on the server, so no task is lost or doubled between the running/completed states, and it
    serializes this client's turns (no two concurrent turns mutating the same state) while different
    clients run in parallel. Replies are pushed to Telegram by the agent's activities, so this
    returns immediately — callers must not await a result.

    ``state_update`` is an optional partial-state merge applied before the turn (e.g. a hotel reply's
    threading headers injected by the webhook); ``None`` for a plain turn.
    """
    settings = get_settings()
    temporal_client = await Client.connect(
        settings.temporal_target,
        data_converter=message_aware_data_converter,
    )
    assert client.telegram_id is not None, "Telegram ID is required"
    task = RunInput(
        client_id=client.id,
        thread_id=client.thread_id,
        telegram_id=client.telegram_id,
        state=update,
        # Resolved here (outside the workflow): get_settings() reads os.environ, which is
        # forbidden inside the Temporal workflow sandbox.
        from_email=settings.mailtrap_from_email or None,
        client_inbox=client.inbox,
        client_email=client.email,
        state_update=state_update,
    )
    await temporal_client.start_workflow(
        AgentQueue.run,
        id=f"queue:{client.thread_id}",
        task_queue=settings.temporal_task_queue,
        # Signal-with-start: signal the running queue, or (re)start it + deliver the signal.
        start_signal=ENQUEUE_SIGNAL,
        start_signal_args=[task],
        # Let a fresh execution reuse the queue id after the previous one drained and completed.
        id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
    )
