from langchain.tools import ToolRuntime
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

from src_v2.agent.state import AgentState
from src_v2.agent.types import AgentContext


@tool
def process_forwarded_email(runtime: ToolRuntime[AgentContext, AgentState]):
    """
    Вызывает разбор предыдущего сообщения пользователя, чтобы извлечь из него информацию о бронировании.
    """
    return Command(
        update={
            "messages": [
                ToolMessage(content="success", tool_call_id=runtime.tool_call_id),
            ],
        }
    )


def _has_tool(msg: AIMessage, tool_name: str) -> bool:
    """
    Проверяет, что в сообщении есть вызов инструмента с указанным именем.
    """
    if msg.tool_calls is None:
        return False
    return any(call["name"] == tool_name for call in msg.tool_calls)


def conditions(state: AgentState):
    """
    Проверяет, что в состоянии есть сообщения от пользователя, которые нужно обработать.
    """
    if len(state["messages"]) > 0:
        if isinstance(msg := state["messages"][-1], AIMessage) and _has_tool(
            msg, "process_forwarded_email"
        ):
            return "email_processor"
    return False
