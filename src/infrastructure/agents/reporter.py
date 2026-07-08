"""ReportBuilder (spec 5.5).

Composes the client-facing report from a booking's topic outcomes. The output is prose, so this
uses a plain ``model.invoke`` (structured output is not appropriate for free text).
"""

from __future__ import annotations

import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from domain.entities import Booking

SYSTEM_PROMPT = """You write a concise, friendly final report to a hotel-booking client, summarizing
what was negotiated with the hotel on each topic. Cost of an upgrade is informational only.

Write plain text. Address the client directly. Group by topic. Mention unresolved or impossible
items honestly and suggest next steps."""


class ReportBuilderAgent:
    """Implements :class:`domain.ports.ReportBuilder`."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    async def build(self, booking: Booking) -> str:
        outcomes = [
            {"topic": t.label, "status": t.status.value, "result": t.result}
            for t in booking.topics
        ]
        summary = json.dumps(
            {
                "hotel": booking.hotel.hotel_name,
                "booking_ref": booking.booking_ref,
                "check_in": str(booking.check_in) if booking.check_in else None,
                "check_out": str(booking.check_out) if booking.check_out else None,
                "topics": outcomes,
            }
        )
        message = await self._model.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"Topic outcomes (JSON):\n{summary}"),
            ]
        )
        report = (message.content if isinstance(message.content, str) else str(message.content)).strip()
        return report or _fallback_report(booking)


def _fallback_report(booking: Booking) -> str:
    lines = [f"Report for {booking.hotel.hotel_name} (ref {booking.booking_ref}):"]
    for t in booking.topics:
        lines.append(f"- {t.label}: {t.status.value}" + (f" — {t.result}" if t.result else ""))
    return "\n".join(lines)
