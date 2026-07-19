"""Build the hotel-conversation ReAct agent graph (runs under Temporal).

A hand-built :class:`langgraph.graph.StateGraph` (model + tools nodes) — not ``create_agent`` —
because the graph is executed by the Temporal LangGraph plugin, which runs each node as an
activity. The agent identifies the hotel email, clarifies the user's wishes, and either forwards
them to the hotel or cancels with a reason.

What used to be ``create_agent`` middleware is applied directly here:

- **self-correction + per-tool retry** — folded into the tool-call wrapper (:func:`_tool_wrapper`
  → :func:`src.agent.middleware.run_tool_call`). A tool's :class:`SelfCorrectionError` becomes a
  corrective ``ToolMessage``; a transient failure is retried per ``config.yaml``.
- **OpenRouter sticky session** — :func:`src.agent.helpers.openrouter.sticky_session_kwargs`
  (``session_id`` in ``extra_body`` for prompt-cache locality).
- **Langfuse tracing** — one trace per turn
  (:mod:`src.agent.helpers.langfuse`); attached per node through ``var_child_runnable_config``.
- **typing indicator** — per node (:func:`src.agent.helpers.telegram.typing`), not workflow-wide,
  so it doesn't fight the agent's own message sends.
"""

from datetime import timedelta
from typing import Literal

from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime
from langgraph.types import Command
from structlog import get_logger
from temporalio.common import RetryPolicy

from src.agent.compaction import compact, compaction_needed
from src.agent.context import EmailContext
from src.agent.helpers.langfuse import inject_langfuse_callback, with_langfuse
from src.agent.helpers.openrouter import sticky_session_kwargs
from src.agent.helpers.telegram import typing
from src.agent.middleware import ToolExecutor, run_tool_call
from src.agent.prompts import SYSTEM_MAIN
from src.agent.state import EmailState
from src.agent.tools import tools
from src.agent.utils import send_telegram_reply
from src.config import get_settings
from src.llm import build_model

__all__ = ["build_email_agent"]

lg = get_logger(__name__)


@with_langfuse
async def model_node(
    state: EmailState,
    runtime: Runtime[EmailContext],  # ty:ignore[invalid-type-arguments]
) -> EmailState:
    lg.info("Model node", message=state["messages"][-1])
    settings = get_settings()
    model = build_model(settings)
    model = model.bind_tools(
        tools, **sticky_session_kwargs(model, runtime.context.get("client_id"))
    )
    async with typing(runtime.context.get("telegram_id")):
        result = await model.ainvoke(
            [
                SYSTEM_MAIN,
                *state["messages"],
            ]
        )
    lg.info("Model result", content=result.content)
    await send_telegram_reply(
        result.content,  # type: ignore
    )
    return {
        "messages": [result],
    }


async def tool_path(state: EmailState) -> Literal["tools", "cleanup", "__end__"]:
    # Model emitted tool calls → run them. Otherwise either compact disposable search/extract
    # output (one final node before END) or, if there is nothing to archive, shortcut to END and
    # skip the cleanup activity entirely.
    if tools_condition(state) == "tools":  # type: ignore
        return "tools"
    if compaction_needed(state["messages"]):
        return "cleanup"
    return "__end__"


async def cleanup_node(state: EmailState) -> EmailState:
    """End-of-turn compaction: replace disposable search/extract tool output with short stubs.

    Pure Python on ``state["messages"]`` — no ``get_context()``, no LLM, no external calls. Each
    stub reuses the heavy message's ``id`` so the stock ``add_messages`` reducer overwrites it in
    place (id-upsert), preserving ``tool_call_id`` / ``name`` and the tool-call ↔ response linkage.
    """
    stubs = compact(state["messages"])
    if stubs:
        lg.info("context.compaction", compacted=len(stubs))
    return {"messages": stubs}


async def _tool_wrapper(request: ToolCallRequest, execute: ToolExecutor) -> ToolMessage | Command:
    """Wrap each tool call: log it, run it under Langfuse, with retry + self-correction."""
    lg.info("Tool call", tool=request.tool_call["name"], input=request.tool_call["args"])
    async with inject_langfuse_callback():
        return await run_tool_call(
            request,
            execute,
            config=get_settings().tool_retry,
        )


_tool_node_impl = ToolNode(
    tools=tools,
    awrap_tool_call=_tool_wrapper,
)


async def tool_node(
    state: EmailState,
    runtime: Runtime[EmailContext],  # ty:ignore[invalid-type-arguments]
) -> EmailState:
    """Run the tools node via its async path.

    ``ToolNode`` is a Runnable with a sync interface. The Temporal LangGraph plugin decides sync vs
    async by ``iscoroutinefunction``: a bare ``ToolNode`` is *not* a coroutine, so the plugin runs it
    via ``asyncio.to_thread`` (sync), which calls ``tool.invoke`` — and our tools are ``async def``
    (``StructuredTool``), whose sync invocation raises "does not support sync invocation". Wrapping
    it in an ``async def`` makes the plugin take the async branch (``tool.ainvoke``). ``runtime`` for
    the tools comes from ``var_child_runnable_config`` (set by the plugin).
    """
    async with typing(runtime.context.get("telegram_id")):
        return await _tool_node_impl.ainvoke(state)


def build_email_agent() -> StateGraph:
    """The hotel-conversation agent graph (model + tools), built for the Temporal LangGraph plugin.

    Each node runs as a Temporal activity (``metadata["execute_in"] = "activity"``) with a timeout
    exceeding the LLM request timeout. The model node allows a couple of retries (a flaky model call
    is worth retrying); tool failures are handled inside :func:`_tool_wrapper` (retry policy
    ``maximum_attempts=1`` here — the per-tool retry loop owns that concern) and surfaced to the
    agent rather than crashing the turn.
    """
    workflow = StateGraph(
        state_schema=EmailState,  # ty:ignore[invalid-argument-type]
        context_schema=EmailContext,  # ty:ignore[invalid-argument-type]
    )
    settings = get_settings()
    common = {
        "execute_in": "activity",
        # Must exceed the LLM request timeout (llm_timeout_seconds, 60s).
        "start_to_close_timeout": timedelta(seconds=settings.llm_activity_timeout_seconds),
        # Bounded retries — the default is unlimited (maximum_attempts=0).
        "retry_policy": RetryPolicy(maximum_attempts=1),
    }
    workflow.add_node(
        "model",
        model_node,
        metadata={
            **common,
        }
        | {
            "retry_policy": RetryPolicy(maximum_attempts=3),
        },
    )
    workflow.add_node(
        "tools",
        tool_node,
        metadata=common,
    )
    workflow.add_node(
        "cleanup",
        cleanup_node,
        # Pure Python on state — no LLM call, so a small fixed timeout (not llm_activity_timeout).
        metadata={**common, "start_to_close_timeout": timedelta(seconds=10)},
    )
    workflow.add_edge(START, "model")
    workflow.add_conditional_edges("model", tool_path)
    # After the tools run, hand control back to the model so it can act on the results. Without this
    # edge the graph ends as soon as the tools node returns (no outgoing edge from "tools").
    workflow.add_edge("tools", "model")
    # End of turn: compact disposable search/extract output, then finish. (The shortcut in
    # ``tool_path`` routes straight to ``__end__`` when there is nothing to archive, so this node
    # only runs when compaction is actually needed.)
    workflow.add_edge("cleanup", END)

    return workflow
