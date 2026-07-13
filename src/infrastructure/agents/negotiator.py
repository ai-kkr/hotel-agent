"""NegotiationAgent (spec 5.4 / design D3, D4).

A ``create_agent`` ReAct agent with read-only web tools, ``response_format=IntentSchema`` and a
per-booking ``checkpointer`` (``thread_id = booking_id``). The agent has **no** ``send_email``
tool — it emits a structured intent; the workflow applies side-effects.

Context persists across turns on the checkpoint saver.
"""

from __future__ import annotations

import json
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from domain.entities import Booking
from domain.enums import TopicStatus
from domain.ids import BookingId, EmailAddress, TopicId
from domain.intents import (
    AgentIntent,
    ClientFollowup,
    ComposeInitial,
    NeedMoreInfo,
    ParseHotelReply,
    Resolved,
    SendEmail,
    TimeoutFollowup,
    TopicResolution,
    Trigger,
)
from infrastructure.agents.schemas import IntentSchema, ResolutionSchema
from infrastructure.agents.tools import WebFetcher, WebSearcher, build_tools
from infrastructure.db.langgraph import thread_config

SYSTEM_PROMPT = """You are a hotel concierge negotiating with a hotel on a client's behalf by email.

Reason step by step. Use web_search / fetch_url if you need hotel details. Then emit your decision
via the structured-response tool:

- To email the hotel: action "send_email" with to/subject/body/language/topics/step.
  `step` is one of: initial, followup1, followup2, clarify.
- When you have parsed a hotel reply and resolved topics: action "resolved" with resolutions
  (each: topic_id, status in resolved|unresolved|cant_progress, result).
- When you need information from the client first: action "need_more_info".

Cost of an upgrade is informational only — never commit the client to payments. Use the topic_ids
given in the booking context."""


class NegotiationAgentImpl:
    """Implements :class:`domain.ports.NegotiationAgent`."""

    def __init__(
        self,
        model: BaseChatModel,
        searcher: WebSearcher,
        fetcher: WebFetcher,
        checkpointer: BaseCheckpointSaver,
        langfuse_callbacks: list | None = None,
    ) -> None:
        self._tools = build_tools(searcher, fetcher)
        self._langfuse_callbacks = langfuse_callbacks or []
        self._agent = create_agent(
            model=model,
            tools=self._tools,
            system_prompt=SYSTEM_PROMPT,
            response_format=IntentSchema,
            checkpointer=checkpointer,
        )

    async def turn(self, booking_id: BookingId, trigger: Trigger, booking: Booking) -> AgentIntent:
        result = await self._agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Booking context:\n{_serialize_booking(booking)}\n\n"
                            f"Trigger:\n{_serialize_trigger(trigger)}"
                        ),
                    }
                ]
            },
            config={
                **thread_config(booking_id),
                "recursion_limit": 10,
                "callbacks": self._langfuse_callbacks,
                "metadata": {"langfuse_session_id": str(booking_id)},
            },
        )
        schema = _coerce(result.get("structured_response"))
        if schema is None:
            return NeedMoreInfo(reason="agent produced no structured intent", question_to_client="")
        return _to_intent(schema, booking)


def _coerce(raw: Any) -> IntentSchema | None:
    if isinstance(raw, IntentSchema):
        return raw
    if isinstance(raw, dict):
        try:
            return IntentSchema.model_validate(raw)
        except Exception:
            return None
    return None


def _serialize_booking(booking: Booking) -> str:
    topics = [
        {"topic_id": t.topic_id, "label": t.label, "status": t.status.value, "result": t.result}
        for t in booking.topics
    ]
    hotel_email = booking.hotel.email.value if booking.hotel.email else None
    return json.dumps(
        {
            "booking_id": booking.booking_id,
            "hotel_name": booking.hotel.hotel_name,
            "hotel_email": hotel_email,
            "language": booking.language,
            "booking_ref": booking.booking_ref,
            "check_in": str(booking.check_in) if booking.check_in else None,
            "check_out": str(booking.check_out) if booking.check_out else None,
            "guests": booking.guests,
            "room_type": booking.room_type,
            "wishes": booking.wishes,
            "topics": topics,
        }
    )


def _serialize_trigger(trigger: Trigger) -> str:
    match trigger:
        case ComposeInitial():
            return json.dumps({"kind": "compose_initial"})
        case ParseHotelReply(body=body, subject=subject):
            return json.dumps({"kind": "hotel_reply", "subject": subject, "body": body})
        case ClientFollowup(body=body):
            return json.dumps({"kind": "client_followup", "body": body})
        case TimeoutFollowup():
            return json.dumps({"kind": "timeout_followup"})


def _resolve_topic(booking: Booking, ref: str) -> TopicId | None:
    ref = ref.strip()
    for topic in booking.topics:
        if topic.topic_id == ref or topic.label.lower() == ref.lower():
            return topic.topic_id
    return None


def _to_intent(schema: IntentSchema, booking: Booking) -> AgentIntent:
    match schema.action:
        case "send_email":
            email = (schema.to or (booking.hotel.email.value if booking.hotel.email else "") or "").strip()
            if not email:
                return NeedMoreInfo(
                    reason="no hotel email available",
                    question_to_client="Please confirm the hotel contact email.",
                )
            topic_ids = [
                tid
                for ref in schema.topics
                for tid in [_resolve_topic(booking, ref)]
                if tid
            ]
            return SendEmail(
                to=EmailAddress(email),
                subject=(schema.subject or "Hotel request").strip(),
                body=(schema.body or "").strip(),
                language=(schema.language or booking.language).strip(),
                topic_ids=topic_ids,
                step=(schema.step or "initial").strip(),
            )
        case "resolved":
            resolutions = [_to_resolution(r, booking) for r in schema.resolutions]
            return Resolved(resolutions=[r for r in resolutions if r is not None])
        case "need_more_info":
            return NeedMoreInfo(
                reason=(schema.reason or "unclear").strip(),
                question_to_client=(schema.question_to_client or "").strip(),
            )
        case _:
            return NeedMoreInfo(reason=f"unknown action: {schema.action!r}", question_to_client="")


def _to_resolution(r: ResolutionSchema, booking: Booking) -> TopicResolution | None:
    topic_id = _resolve_topic(booking, r.topic_id)
    if topic_id is None:
        return None
    try:
        status = TopicStatus(r.status)
    except ValueError:
        status = TopicStatus.RESOLVED
    result = (r.result or "").strip() or "n/a"
    if status is TopicStatus.RESOLVED and not (r.result or "").strip():
        return None
    return TopicResolution(topic_id=topic_id, status=status, result=result)
