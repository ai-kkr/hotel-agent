"""Tools available to the search-agent node of the email graph.

``set_hotel_email`` is the terminal action of the search loop: the agent calls it once it is
confident it has found the hotel's contact address, which both records the email and ends the
search.
"""

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from infrastructure.logging import get_logger
from src_v2.agent.tools import search_tools
from src_v2.agent.types import AgentContext
from src_v2.utils.validators import EmailOptional

from ...state import AgentState

__all__ = ["search_tool_node", "set_hotel_email", "tools"]

log = get_logger(__name__)


@tool
def set_hotel_email(
    email: EmailOptional,
    runtime: ToolRuntime[AgentContext, AgentState],
):
    """Record the hotel contact email you found so the graph can finish.

    Call this once you have confidently identified the hotel's contact email (from the booking
    confirmation or via search_internet / extract_web_page). This ends the search.

    Args:
        email: The hotel's contact email address.
    """
    log.info("tool.set_hotel_email", email=str(email))
    return Command(
        update={
            "hotel_email": email,
            "messages": [
                ToolMessage(
                    content="Success",
                    tool_call_id=runtime.tool_call_id,
                ),
            ],
        }
    )


tools = [*search_tools, set_hotel_email]
search_tool_node = ToolNode(tools=tools, name="search_tools")
