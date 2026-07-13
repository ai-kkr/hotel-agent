"""Wiring of the email-extraction graph.

Flow:

    START -> email_extractor -+-> END (hotel email already in confirmation)
                              +-> email_extractor (retry on parse failure)
                              +-> search_agent -> tools -> search_agent ... -> get_user_intention -> END

``route_from_extractor`` decides whether extraction succeeded (or needs retry / a web search),
``route_after_search_agent`` drives the tool-calling search loop and hands off to the terminal
``get_user_intention`` node once the hotel email is known.
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from infrastructure.logging import get_logger
from src_v2.agent.types import AgentContext

from .nodes import (
    email_extractor_node,
    get_user_intention,
    get_user_intention_loop,
    search_agent_node,
    send_user_intention_to_hotel,
)
from .state import EmailInputState, EmailOutputState, EmailState, SendEmailToHotelOutputState
from .tools import search_tool_node

__all__ = [
    "get_email_graph",
    "route_after_search_agent",
    "route_after_user_intention",
    "route_from_extractor",
    "workflow",
]

log = get_logger(__name__)


workflow = StateGraph[
    EmailState,  # ty:ignore[invalid-type-arguments]
    AgentContext,
    EmailInputState,  # ty:ignore[invalid-type-arguments]
](
    state_schema=EmailState,
    context_schema=AgentContext,
    output_schema=SendEmailToHotelOutputState,
    input_schema=EmailInputState,
)

workflow.add_node("email_extractor", email_extractor_node)
workflow.add_node("tools", search_tool_node)
workflow.add_node("search_agent", search_agent_node)
workflow.add_node("get_user_intention", get_user_intention)
workflow.add_node("get_user_intention_loop", get_user_intention_loop)
workflow.add_node("send_letter_to_hotel", send_user_intention_to_hotel)


def route_from_extractor(state: EmailOutputState):
    if state.get("hotel_email"):
        log.info("route.from_extractor", next_="get_user_intention", reason="hotel_email_known")
        return "get_user_intention"
    if state.get("parsed_email") is None and state.get("attempts", 0) < 3:
        log.info("route.from_extractor", next_="email_extractor", reason="retry_extraction")
        return "email_extractor"
    log.info("route.from_extractor", next_="search_agent", reason="no_email_need_search")
    return "search_agent"


def route_after_search_agent(state: EmailOutputState):
    if state.get("hotel_email"):
        log.info("route.after_search_agent", next_="get_user_intention", reason="hotel_email_known")
        return "get_user_intention"
    if state.get("search_rounds", 0) >= 3:
        log.info("route.after_search_agent", next_=END, reason="search_rounds_exhausted")
        return END
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        log.info("route.after_search_agent", next_="tools", reason="tool_calls_pending")
        return "tools"
    log.info("route.after_search_agent", next_=END, reason="no_tool_calls")
    return END


def route_after_user_intention(state: EmailOutputState):
    """Skip the wishes loop when wishes were already found in the cover note."""
    if state.get("wishes"):
        log.info("route.after_user_intention", next_="send_letter_to_hotel", reason="wishes_known")
        return "send_letter_to_hotel"
    log.info("route.after_user_intention", next_="get_user_intention_loop", reason="no_wishes")
    return "get_user_intention_loop"


workflow.add_edge(START, "email_extractor")
workflow.add_conditional_edges("email_extractor", route_from_extractor)
workflow.add_conditional_edges("search_agent", route_after_search_agent)
workflow.add_edge("tools", "search_agent")
workflow.add_conditional_edges("get_user_intention", route_after_user_intention)
# ``get_user_intention_loop`` has no static outgoing edge: it routes via the Command it returns
# (→ send_letter_to_hotel on success, → END on cancel / exhausted attempts).
workflow.add_edge("send_letter_to_hotel", END)


def get_email_graph(checkpointer: BaseCheckpointSaver):
    return workflow.compile(checkpointer=checkpointer)
