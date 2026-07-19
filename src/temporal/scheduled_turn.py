"""The trivial workflow a Temporal Schedule starts on each fire.

Why this exists: a Temporal Schedule action (``ScheduleActionStartWorkflow``) can only *start* a
fresh workflow run — there is no signal-with-start in the Python SDK. But :class:`AgentQueue`
receives turns via its ``add_task`` *signal*, and :func:`agent_step` delivers them via
signal-with-start so a fire serializes against a running queue. To bridge that, each fire starts
this workflow, whose single activity (:func:`enqueue_scheduled_turn`) performs that same
signal-with-start onto ``queue:{thread_id}``. A scheduled firing is therefore indistinguishable from
a guest turn: it lands on the per-client queue, runs as an ``AgentWorkflow`` child, and loads the
latest persisted ``EmailState``.

The schedule's workflow id is fixed per task (``kkr-kick:{client_id}:{task_key}``). The action's
``workflow_id_reuse_policy`` is left at the server default (ALLOW_DUPLICATE), so once a fire's run
completes the closed id is reused on the next fire. The default overlap policy (SKIP) harmlessly
drops a fire only if the previous sub-second run is somehow still going.
"""

from datetime import timedelta

from temporalio import workflow

from src.temporal.activities import enqueue_scheduled_turn
from src.temporal.model import RunInput


@workflow.defn
class ScheduledTurn:
    """One-activity workflow: enqueue a scheduled turn onto the client's queue, then exit."""

    @workflow.run
    async def run(self, run_input: RunInput) -> None:
        await workflow.execute_activity(
            enqueue_scheduled_turn,
            run_input,
            start_to_close_timeout=timedelta(seconds=30),
        )
