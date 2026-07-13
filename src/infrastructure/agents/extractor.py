"""ConfirmationExtractor (spec 5.1).

Uses ``model.with_structured_output`` to pull typed booking data + wishes from a forwarded
confirmation. The model separates the client's cover note from the forwarded block.
"""

from __future__ import annotations

from datetime import date

from langchain_core.language_models import BaseChatModel

from domain.events import ConfirmForward
from domain.extraction import ExtractedBooking
from domain.ids import EmailAddress
from infrastructure.agents.schemas import ExtractedBookingSchema

SYSTEM_PROMPT = """You extract structured booking data from a forwarded hotel confirmation email.

The user message contains the sender's cover note and the forwarded confirmation. Extract every
field you can confidently find. Put any free-text requests the SENDER added outside the forwarded
block into `wishes`. Set `confidence` to your overall confidence (0..1)."""


class ConfirmationExtractorAgent:
    """Implements :class:`domain.ports.ConfirmationExtractor`."""

    def __init__(self, model: BaseChatModel, confidence_threshold: float = 0.7) -> None:
        # ``method="function_calling"`` returns the schema as a tool-call argument (clean JSON).
        # The default JSON-schema/response_format path breaks on OpenAI-compatible models (e.g. GLM
        # via the Z.AI coding endpoint) that wrap JSON in markdown fences.
        self._structured = model.with_structured_output(ExtractedBookingSchema, method="function_calling")
        self._threshold = confidence_threshold

    async def extract(self, event: ConfirmForward) -> ExtractedBooking:
        raw = await self._structured.ainvoke(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Sender's cover note:\n{event.cover_text}\n\n"
                        f"Forwarded confirmation:\n{event.forwarded_payload}"
                    ),
                },
            ]
        )
        schema = raw if isinstance(raw, ExtractedBookingSchema) else ExtractedBookingSchema.model_validate(raw)
        return _to_domain(schema, self._threshold)


def _to_domain(schema: ExtractedBookingSchema, threshold: float) -> ExtractedBooking:
    hotel_email = schema.hotel_email  # already EmailStr-validated (or None) by the schema
    return ExtractedBooking(
        hotel_name=(schema.hotel_name or "").strip() or "unknown",
        confidence=schema.confidence,
        hotel_email=EmailAddress(hotel_email) if hotel_email else None,
        hotel_website=(schema.hotel_website or "").strip() or None,
        booking_ref=(schema.booking_ref or "").strip() or None,
        check_in=_parse_date(schema.check_in),
        check_out=_parse_date(schema.check_out),
        guests=[g.strip() for g in schema.guests if g.strip()],
        room_type=(schema.room_type or "").strip() or None,
        wishes=[w.strip() for w in schema.wishes if w.strip()],
        missing_required=_missing_required(schema),
        low_confidence=schema.confidence < threshold,
    )


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _missing_required(schema: ExtractedBookingSchema) -> list[str]:
    missing: list[str] = []
    if not (schema.hotel_name or "").strip():
        missing.append("hotel_name")
    if not _parse_date(schema.check_in):
        missing.append("check_in")
    if not _parse_date(schema.check_out):
        missing.append("check_out")
    if not (schema.booking_ref or "").strip():
        missing.append("booking_ref")
    return missing
