"""Build the hotel-conversation ReAct agent.

Wires the hotel-conversation tools + the shared search tools into a single
:func:`langchain.agents.create_agent` graph. The agent identifies the hotel email, clarifies the
user's wishes, and either forwards them to the hotel or cancels with a reason.
"""

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.config import get_settings

from .context import EmailContext
from .middleware import (
    OpenRouterStickySessionMiddleware,
    SelfCorrectionMiddleware,
    ToolRetryMiddleware,
)
from .prompts import SYSTEM_MAIN
from .state import EmailState
from .tools import tools

__all__ = ["build_email_agent"]


def build_email_agent(model: BaseChatModel, checkpointer: BaseCheckpointSaver):
    # Lazy import: src.context imports this builder at module load (it builds ``email_graph``),
    # so importing get_context at the top would create a context↔agent cycle.
    #
    # Middleware order = nesting order (first is outermost). ``SelfCorrectionMiddleware`` is
    # outermost so it catches :class:`SelfCorrectionError` raised anywhere below;
    # ``ToolRetryMiddleware`` sits inside it (a self-correction error propagates through it
    # unretried, while transient tool failures get retried and only surface as a ToolMessage on
    # exhaustion); the OpenRouter sticky-session middleware wraps the model call itself.
    settings = get_settings()
    return create_agent(
        model=model,
        tools=tools,
        middleware=[
            SelfCorrectionMiddleware(),
            ToolRetryMiddleware(settings.tool_retry),
            OpenRouterStickySessionMiddleware(),
        ],
        system_prompt=SYSTEM_MAIN,
        state_schema=EmailState,
        context_schema=EmailContext,
        checkpointer=checkpointer,
    )
