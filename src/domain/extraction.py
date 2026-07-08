"""Result of confirmation extraction (produced by the LangGraph ``ConfirmationExtractor``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from domain.ids import EmailAddress

# Required booking fields that must be extracted above the confidence threshold.
REQUIRED_FIELDS: tuple[str, ...] = ("hotel_name", "check_in", "check_out", "booking_ref")


@dataclass(frozen=True)
class ExtractedBooking:
    """Structured booking data pulled from a forwarded confirmation, plus client wishes."""

    hotel_name: str
    confidence: float
    hotel_email: EmailAddress | None = None
    hotel_website: str | None = None
    booking_ref: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    guests: list[str] = field(default_factory=list)
    room_type: str | None = None
    wishes: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    low_confidence: bool = False

    def __post_init__(self) -> None:
        if not self.hotel_name.strip():
            raise ValueError("hotel_name must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")

    @property
    def is_confident(self) -> bool:
        """Confident when overall confidence is acceptable AND no required field is missing."""
        return not self.missing_required and not self.low_confidence

    def hotel_language_hint(self) -> str | None:
        """A best-effort language hint from the website TLD; None if unknown."""
        if not self.hotel_website:
            return None
        tld = self.hotel_website.rsplit(".", 1)[-1].split("/")[0].lower()
        cc_to_lang = {"fr": "fr", "de": "de", "es": "es", "it": "it", "ru": "ru", "jp": "ja"}
        return cc_to_lang.get(tld)
