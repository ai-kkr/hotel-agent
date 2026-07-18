from datetime import timedelta

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from temporalio import workflow
from temporalio.contrib.langgraph import graph
from temporalio.contrib.workflow_streams import WorkflowStream

from src.agent import EmailContext
from src.agent.state import EmailState
from src.temporal.activities import SaveStateInput, load_state, save_state
from src.temporal.model import RunInput


@workflow.defn
class AgentWorkflow:
    def __init__(self) -> None:
        self.stream = WorkflowStream()

    @workflow.run
    async def run_user(
        self,
        input: RunInput,
    ) -> EmailState:
        workflow.logger.info(
            "Running agent workflow for client_id=%s, thread_id=%s",
            input.client_id,
            input.thread_id,
        )
        saver = InMemorySaver()
        g = graph("agent").compile(checkpointer=saver)

        context = _build_context(input)
        config = _build_config(input)

        state = await workflow.execute_activity(
            load_state,
            input.client_id,
            start_to_close_timeout=timedelta(seconds=10),
        )  # type: ignore
        if state is not None:
            g.update_state(config=config, values=state)
        # Optional partial-state merge for this turn (e.g. a hotel reply's threading headers,
        # injected by the webhook). Applied after loading persisted state, before the turn runs.
        if input.state_update:
            g.update_state(config=config, values=input.state_update)
        # Typing is managed per-node (model_node / tool_node) via ``bot_typing`` — a workflow-wide
        # loop would fight the agent's own message sends (each send clears the indicator).
        state: EmailState = await g.ainvoke(
            input.state,
            context=context,
            config=config,
        )  # type: ignore
        await workflow.execute_activity(
            save_state,
            SaveStateInput(
                client_id=input.client_id,
                state=state,
            ),
            start_to_close_timeout=timedelta(seconds=10),
        )
        workflow.logger.info(
            "Agent workflow completed",
        )
        return state


def _build_config(input: RunInput) -> RunnableConfig:
    # One AgentWorkflow execution == one agent turn, so run_id is a stable, unique-per-turn value.
    # Derive a deterministic 32-hex Langfuse trace id from it: stable across replay (uuid4 would
    # re-roll and break determinism), and shared by every node activity in the turn so they all land
    # in ONE Langfuse trace instead of each starting their own.
    import hashlib

    trace_id = hashlib.sha256(workflow.info().run_id.encode()).hexdigest()[:32]
    return RunnableConfig(
        configurable={
            "thread_id": input.thread_id,
        },
        metadata={
            "langfuse_session_id": input.thread_id,
            "langfuse_user_id": str(input.client_id),
            "langfuse_trace_id": trace_id,
        },
    )


def _build_context(input: RunInput) -> EmailContext:
    return EmailContext(
        from_email=input.from_email,
        reply_to=input.client_inbox,
        user_email=input.client_email,
        client_id=input.client_id,
        telegram_id=input.telegram_id,
    )
