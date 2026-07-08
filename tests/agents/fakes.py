"""Deterministic fake chat model for agent tests.

Supports the LangChain surface the agents use: ``_generate`` (scripted ``AIMessage`` responses,
which may carry ``tool_calls``), ``bind_tools`` (no-op), and ``with_structured_output`` (returns a
runnable popping scripted objects). This lets ``create_agent`` + ``response_format`` run without a
real LLM: a scripted response that calls the structured-response tool (named after the schema)
populates ``structured_response``.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import Field


class FakeChatModel(BaseChatModel):
    responses: list[AIMessage] = Field(default_factory=list)
    structured: list[Any] = Field(default_factory=list)

    def with_response(self, message: AIMessage) -> FakeChatModel:
        self.responses.append(message)
        return self

    def with_structured(self, obj: Any) -> FakeChatModel:
        self.structured.append(obj)
        return self

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(self, messages: object, stop: object = None, run_id: object = None, **kwargs: object) -> ChatResult:
        message = self.responses.pop(0) if self.responses else AIMessage(content="done")
        return ChatResult(generations=[ChatGeneration(message=message)])

    def bind_tools(self, tools: object, **kwargs: object) -> FakeChatModel:
        return self

    def with_structured_output(self, schema: object, **kwargs: object) -> RunnableLambda:  # type: ignore[override]
        def _pop(_: object) -> Any:
            return self.structured.pop(0) if self.structured else None

        return RunnableLambda(_pop)


def tool_call(name: str, args: dict[str, Any]) -> AIMessage:
    """Build an AIMessage that calls a tool (used to drive the agent loop / structured output)."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": name, "type": "tool_call"}])
