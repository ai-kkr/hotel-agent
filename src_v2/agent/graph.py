from langgraph.graph import StateGraph
from langgraph.runtime import Runtime

from .prompts import SYSTEM_MESSAGE
from .state import AgentState
from .types import AgentContext

workflow = StateGraph(
    state_schema=AgentState,  # ty:ignore[invalid-argument-type]
    context_schema=AgentContext,
)


async def agent_node(state: AgentState, runtime: Runtime[AgentContext]) -> AgentState:
    model = runtime.context.model.bind_tools(tools)
    messages = [
        SYSTEM_MESSAGE,
        *state["messages"],
    ]
    response = await model.ainvoke(messages)
    return {"messages": [response]}
