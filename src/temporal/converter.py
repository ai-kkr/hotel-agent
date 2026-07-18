"""Temporal data converter that round-trips langchain messages.

The default ``pydantic_data_converter`` decodes activity payloads with ``type_hint=Any`` — activity
args carry no per-arg hints — so ``BaseMessage`` objects nested in the agent state come back as plain
dicts, losing the subclass (``AIMessage``/``HumanMessage``/…). That breaks anything that
``isinstance``-checks messages, e.g. ``ToolNode._parse_input`` raising "No AIMessage found in input".

This converter keeps pydantic's JSON encoding but, on decode, recursively re-validates any dict
shaped like a langchain message (``type`` in the message discriminator set) as ``AnyMessage`` —
langchain's discriminated union, which pydantic maps to the correct subclass via the ``type`` field.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from langchain_core.messages import AnyMessage
from langgraph.types import Command
from pydantic import TypeAdapter
from temporalio.api.common.v1 import Payload
from temporalio.contrib.pydantic import (
    PydanticJSONPlainPayloadConverter,
    PydanticPayloadConverter,
)
from temporalio.converter import DataConverter

_ANYMESSAGE = TypeAdapter(AnyMessage)

#: ``type`` discriminator values used by langchain messages (the members of ``AnyMessage``).
_MESSAGE_TYPES = frozenset({"system", "human", "ai", "tool", "function", "chat", "remove", "modal"})


def _looks_like_command(value: dict) -> bool:
    """True if ``value`` is a serialized langgraph ``Command`` (has ``update`` + a nav field)."""
    return "update" in value and any(k in value for k in ("goto", "resume", "graph"))


def _reconstruct(value: Any) -> Any:
    """Recursively restore langchain messages and langgraph ``Command`` objects after decode.

    Activity payloads are decoded against their type hint (``ActivityInput`` dataclass, ``args`` is a
    tuple of plain ``Any``), so langchain ``BaseMessage`` and langgraph ``Command`` objects nested in
    the state arrive as plain dicts and lose their type. That breaks ``isinstance`` checks downstream
    — ``ToolNode._parse_input`` needs real ``AIMessage`` instances, and langgraph's
    ``_get_updates`` only accepts a ``list[Command]`` when the elements *are* ``Command`` objects (a
    list of dicts raises ``InvalidUpdateError: Expected dict``).

    This walks every container the payload can contain — tuples (activity ``args``), dataclasses (the
    activity input itself), lists and dicts — and re-validates:
      - message-shaped dicts (``type`` in the discriminator set) as ``AnyMessage`` (restores the
        subclass via the ``type`` field);
      - command-shaped dicts (``update`` + a nav field) as ``Command``.

    Note: nodes that return a *single* ``Command`` are handled by the LangGraph plugin itself (it
    reconstructs them from ``output.langgraph_command``) — that path is untouched here. Our
    ``ToolNode`` always returns a ``list[Command]`` (it goes through ``output.result``), so this
    restoration is what lets langgraph accept it.
    """
    # Activity args arrive as a tuple; recurse element-wise, preserving the type.
    if isinstance(value, tuple):
        return tuple(_reconstruct(v) for v in value)
    if isinstance(value, list):
        return [_reconstruct(v) for v in value]
    # The activity input itself (e.g. ActivityInput) is a dataclass — recurse its fields and rebuild.
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return type(value)(
            **{f.name: _reconstruct(getattr(value, f.name)) for f in dataclasses.fields(value)}
        )
    if isinstance(value, dict):
        if _looks_like_command(value):
            return Command(
                graph=value.get("graph"),
                update=_reconstruct(value.get("update")),
                resume=value.get("resume"),
                goto=_reconstruct(value.get("goto")),
            )
        if value.get("type") in _MESSAGE_TYPES:
            try:
                return _ANYMESSAGE.validate_python(value)
            except Exception:
                pass  # not actually a message — treat as a plain dict below
        return {k: _reconstruct(v) for k, v in value.items()}
    return value


class _MessageAwareJSONConverter(PydanticJSONPlainPayloadConverter):
    """Pydantic JSON converter that reconstructs langchain messages and Commands on decode."""

    def from_payload(self, payload: Payload, type_hint: type | None = None) -> Any:
        return _reconstruct(super().from_payload(payload, type_hint))


class MessageAwarePayloadConverter(PydanticPayloadConverter):
    """Pydantic converter whose ``json/plain`` stage reconstructs langchain messages on decode."""

    def __init__(self) -> None:
        super().__init__()
        # Swap the plain pydantic JSON converter for the message-aware one (keyed by its encoding).
        self.converters[_MessageAwareJSONConverter().encoding.encode()] = (
            _MessageAwareJSONConverter()
        )


#: Drop-in replacement for ``pydantic_data_converter`` that preserves langchain message subclasses
#: across the workflow↔activity boundary.
message_aware_data_converter = DataConverter(payload_converter_class=MessageAwarePayloadConverter)
