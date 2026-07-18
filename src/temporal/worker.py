import asyncio

from temporalio import workflow
from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from src.agent.agent import build_email_agent
from src.agent.tracing import init_langfuse
from src.config import get_settings
from src.logging import get_logger
from src.temporal.activities import load_state, save_state
from src.temporal.agent_runner import AgentWorkflow
from src.temporal.queue import AgentQueue

with workflow.unsafe.imports_passed_through():
    from src.temporal.converter import message_aware_data_converter


lg = get_logger(__file__)


async def run_worker():

    setting = get_settings()
    init_langfuse(setting)

    client = await Client.connect(
        setting.temporal_target,
        data_converter=message_aware_data_converter,
    )
    plugin = LangGraphPlugin(
        graphs={"agent": build_email_agent()},
        # streaming_topic="tokens",
    )
    worker = Worker(
        client,
        task_queue=setting.temporal_task_queue,
        workflows=[AgentQueue, AgentWorkflow],
        activities=[load_state, save_state],
        plugins=[plugin],
        workflow_runner=UnsandboxedWorkflowRunner(),
    )
    lg.info("Starting Temporal worker...")
    task = asyncio.create_task(worker.run())
    return worker, task
