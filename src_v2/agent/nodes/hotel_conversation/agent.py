"""Build the hotel-conversation ReAct agent.

Wires the hotel-conversation tools + the shared search tools into a single
:func:`langchain.agents.create_agent` graph. The agent identifies the hotel email, clarifies the
user's wishes, and either forwards them to the hotel or cancels with a reason.
"""

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from src_v2.agent.prompts import SYSTEM_HOTEL_CONVERSATION
from src_v2.agent.tools import search_tools

from .context import EmailContext
from .middleware import SelfCorrectionMiddleware
from .state import EmailState
from .tools import tools as hotel_conversation_tools

__all__ = ["build_email_agent"]


def build_email_agent(model: BaseChatModel, checkpointer: BaseCheckpointSaver):
    # Lazy import: src_v2.context imports this builder at module load (it builds ``email_graph``),
    # so importing get_context at the top would create a context↔agent cycle.

    return create_agent(
        model=model,
        tools=[
            *hotel_conversation_tools,
            *search_tools,
        ],
        middleware=[SelfCorrectionMiddleware()],
        system_prompt=SYSTEM_HOTEL_CONVERSATION,
        state_schema=EmailState,
        context_schema=EmailContext,
        checkpointer=checkpointer,
    )
