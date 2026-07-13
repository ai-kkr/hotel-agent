from dataclasses import dataclass
from typing import Literal, TypedDict

from langchain.chat_models import BaseChatModel
from langgraph.graph import StateGraph
from pydantic import BaseModel
from tavily import TavilyClient

from domain.ports import OutboundMailGateway

from .state import AgentState


@dataclass
class AgentContext:
    model: BaseChatModel
    tavily_client: TavilyClient
    outbound_mail_gateway: OutboundMailGateway
    from_email: str


type AgentWorkflow = StateGraph[AgentState, AgentContext]  # ty:ignore[invalid-type-arguments]


class StructuredOutputWithRaw[T](TypedDict):
    raw: str
    parsed: T
    parsing_error: Exception | None


class MessageText(BaseModel):
    text: str
    is_confirm: bool = False
    type: Literal["message_text"] = "message_text"
