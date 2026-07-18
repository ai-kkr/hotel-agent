from collections import deque

from temporalio import workflow

from src.temporal.agent_runner import AgentWorkflow
from src.temporal.model import RunInput

#: Name of the enqueue signal. The queue is driven by signal-with-start
#: (``start_workflow(..., start_signal=ENQUEUE_SIGNAL, start_signal_args=[task])``), so this must
#: match the ``@workflow.signal`` method name below.
ENQUEUE_SIGNAL = "add_task"


@workflow.defn
class AgentQueue:
    """Serialize agent turns for a single client (one queue workflow per ``thread_id``).

    Driven by signal-with-start from the client: if a queue for this client is already running the
    signal just appends to its deque; otherwise the workflow is (re)started and the signal delivers
    the first task — atomically on the server, so no task is lost or doubled between the running and
    completed states. Turns run one at a time as :class:`AgentWorkflow` child workflows (a client's
    state is never mutated by two turns at once); different clients run in parallel. The workflow
    exits when its deque drains, so the next enqueue starts a fresh execution (bounded history).
    """

    def __init__(self) -> None:
        self._tasks: deque[RunInput] = deque()
        self._counter = 0

    @workflow.run
    async def run(self) -> None:
        # The first task arrives via the start signal; wait for it before inspecting the deque so a
        # signal delivered in the same activation as start is observed, not raced past.
        await workflow.wait_condition(lambda: len(self._tasks) > 0)
        # ``run_id`` is stable across replay, so child IDs (run_id + a monotonic counter) are
        # deterministic on replay yet unique across executions — each restart gets a fresh run_id,
        # avoiding collisions with child workflows from a previous execution.
        run_id = workflow.info().run_id
        while self._tasks:
            current = self._tasks.popleft()
            self._counter += 1
            await workflow.execute_child_workflow(
                AgentWorkflow.run_user,
                current,
                id=f"{current.thread_id}-{run_id}-{self._counter}",
            )

    @workflow.signal
    async def add_task(self, task: RunInput) -> None:
        """Append a task to the queue (delivered via signal-with-start)."""
        self._tasks.append(task)
