"""Pydantic schemas for agent structured output (``with_structured_output`` / ``response_format``).

These are the typed contracts the models must produce. The agents map them onto domain types.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

# Models sometimes emit sentinel strings ("null"/"N/A"/"-") for an absent email; normalize those to
# None before EmailStr validation so parsing doesn't fail the activity.
_ABSENT_EMAIL_SENTINELS = {"", "null", "none", "n/a", "na", "-", "--"}


def _optional_email_before(value: Any) -> Any:
    """``mode="before"`` normalizer for optional EmailStr fields: map sentinels/blanks to None."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in _ABSENT_EMAIL_SENTINELS:
            return None
        return stripped
    return value


class ExtractedBookingSchema(BaseModel):
    """Structured extraction of a forwarded booking confirmation."""

    hotel_name: str
    hotel_email: EmailStr | None = None
    hotel_website: str | None = None
    booking_ref: str | None = None
    check_in: str | None = Field(default=None, description="YYYY-MM-DD")  # type: ignore[assignment]
    check_out: str | None = Field(default=None, description="YYYY-MM-DD")  # type: ignore[assignment]
    guests: list[str] = Field(default_factory=list)
    room_type: str | None = None
    wishes: list[str] = Field(
        default_factory=list, description="free-text requests the sender added"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("hotel_email", mode="before")
    @classmethod
    def _normalize_hotel_email(cls, value: Any) -> Any:
        return _optional_email_before(value)


class ContactSchema(BaseModel):
    """Discovered hotel contact + correspondence language."""

    email: EmailStr | None = None
    language: str = Field(default="en", description="ISO-639-1, e.g. en, fr, es")
    website: str | None = None
    found: bool = False

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: Any) -> Any:
        return _optional_email_before(value)


class ResolutionSchema(BaseModel):
    """Outcome of one negotiation topic after parsing a hotel reply."""

    topic_id: str
    status: Literal["resolved", "unresolved", "cant_progress"]
    result: str = ""


class IntentSchema(BaseModel):
    """The negotiation agent's decision, emitted via the structured-response tool."""

    action: Literal["send_email", "resolved", "need_more_info"]
    # send_email
    to: str | None = None
    subject: str | None = None
    body: str | None = None
    language: str | None = None
    topics: list[str] = Field(default_factory=list)
    step: str | None = None
    # resolved
    resolutions: list[ResolutionSchema] = Field(default_factory=list)
    # need_more_info
    reason: str | None = None
    question_to_client: str | None = None
