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
from langchain_core.messages import RemoveMessage, SystemMessage, ToolMessage
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
from src.agent.summarization import (
    split_index,
    summarization_needed,
    summarize_prefix,
)
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
    # Running summary (if any) is injected right after the system prompt as a SystemMessage. It only
    # changes at summarization events (rare), so the [SYSTEM_MAIN + summary + messages] prefix stays
    # cache-stable between them — consistent with the OpenRouter sticky-session cache locality.
    summary = state.get("conversation_summary")
    invoke_input: list = (
        [SYSTEM_MAIN, SystemMessage(content=summary), *state["messages"]]
        if summary
        else [SYSTEM_MAIN, *state["messages"]]
    )
    async with typing(runtime.context.get("telegram_id")):
        result = await model.ainvoke(invoke_input)
    lg.info("Model result", content=result.content)
    await send_telegram_reply(
        result.content,  # type: ignore
    )
    # Reactive context-size signal: the provider's own count of the input we just sent. Read on the
    # NEXT entry via ``summarize_check`` — so the first model call (no past usage yet) is unprotected.
    usage = result.usage_metadata or {}
    return {
        "messages": [result],
        "last_prompt_tokens": int(usage.get("input_tokens", 0)),
    }


async def summarize_check(state: EmailState) -> Literal["summarize", "model"]:
    """Gate entry to the model node on the soft token threshold.

    Reactive — checks the *previous* call's reported ``input_tokens``. When there is no past usage
    yet (``last_prompt_tokens`` absent/0, i.e. the first call of a conversation), it routes straight
    to the model: the threshold has no signal to act on.

    Async like every other node/branch (``model_node``, ``tool_path``, …) — Temporal runs the graph
    via the async API. The entry branch is evaluated during state seeding in
    [src/temporal/agent_runner.py](src/temporal/agent_runner.py), which MUST use ``aupdate_state``
    (not the sync ``update_state``): the sync superstep can't drive an async branch and raises
    ``TypeError: No synchronous function provided``.
    """
    settings = get_settings()
    if summarization_needed(
        state.get("last_prompt_tokens", 0),
        settings.summarize_token_threshold,
    ):
        return "summarize"
    return "model"


@with_langfuse
async def summarize_node(
    state: EmailState,
    runtime: Runtime[EmailContext],  # ty:ignore[invalid-type-arguments]
) -> EmailState:
    """Compress the old message prefix into ``conversation_summary`` and remove it.

    Notifies the guest first (the extra LLM call may take several seconds), then computes a
    tool-call-safe split, summarizes the prefix in one shot, and returns ``RemoveMessage`` entries
    for the prefix (the stock ``add_messages`` reducer drops them by id) plus the new summary. A
    recency window of the most recent messages is always retained. If the whole history fits the
    recency window (nothing to compress), this is a no-op — no notification, no call.

    The summarize model is built **identically to ``model_node``** (same provider config, same bound
    tools, same OpenRouter sticky session via the client id) and passed to
    :func:`summarize_prefix`. The summarize call must be a cache continuation of the long thread, not
    a separate request — any model-config difference busts the prefix cache.
    """
    settings = get_settings()
    messages = state["messages"]
    cut = split_index(messages, settings.summarize_keep_last_messages)
    if cut <= 0:
        # Nothing compressible — empty ``messages`` update is a reducer no-op.
        return {"messages": []}
    prefix = list(messages[:cut])
    await send_telegram_reply(
        "⏳ Переписка стала длинной — подвожу итог, чтобы ничего не потерять. "
        "Это займёт немного времени."
    )
    # Identical to model_node's model construction — keeps the prefix cache valid (see summarize_prefix).
    model = build_model(settings)
    model = model.bind_tools(
        tools, **sticky_session_kwargs(model, runtime.context.get("client_id"))
    )
    new_summary = await summarize_prefix(model, prefix, state.get("conversation_summary"))
    lg.info("context.summarization", summarized=len(prefix), kept=len(messages) - cut)
    removals = [RemoveMessage(id=m.id) for m in prefix if m.id is not None]
    return {  # ty:ignore[invalid-return-type]  (RemoveMessage isn't in the messages union; add_messages drops by id)
        "conversation_summary": new_summary,
        "messages": removals,  # ty:ignore[invalid-argument-type]
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


@with_langfuse
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
    workflow.add_node(
        "summarize",
        summarize_node,
        # Full LLM call — same timeout budget as the model node, and a couple of retries like it.
        metadata={
            **common,
            "retry_policy": RetryPolicy(maximum_attempts=3),
        },
    )
    # Entry (and re-entry after tools) is gated on the soft token threshold: route through the
    # ``summarize`` node when the previous model call already exceeded it, else straight to ``model``.
    # ``summarize_check`` is a pure routing function (no activity); the first call of a conversation
    # has no past usage, so it goes straight to the model.
    workflow.add_conditional_edges(START, summarize_check)
    workflow.add_conditional_edges("tools", summarize_check)
    workflow.add_edge("summarize", "model")
    workflow.add_conditional_edges("model", tool_path)
    # End of turn: compact disposable search/extract output, then finish. (The shortcut in
    # ``tool_path`` routes straight to ``__end__`` when there is nothing to archive, so this node
    # only runs when compaction is actually needed.)
    workflow.add_edge("cleanup", END)

    return workflow
