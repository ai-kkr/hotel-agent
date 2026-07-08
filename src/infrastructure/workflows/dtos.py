"""Serializable DTOs crossing the Temporal activity/workflow boundary.

Workflows must stay deterministic, so they exchange plain data (not live domain objects or ports).
These are pydantic models — Temporal's default data converter serializes them.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TopicStatusValue = Literal["open", "resolved", "unresolved", "cant_progress"]
LifecycleValue = Literal[
    "intake",
    "extracted",
    "contact_ready",
    "in_conversation",
    "awaiting_reply",
    "topics_resolved",
    "report_sent",
    "awaiting_client_followup",
    "cant_progress",
    "cancelled",
]
ActionValue = Literal["send_email", "resolved", "need_more_info"]


class HotelContactData(BaseModel):
    hotel_name: str
    email: str | None = None
    website: str | None = None
    language: str | None = None
    discovered: bool = False


class TopicData(BaseModel):
    topic_id: str
    label: str
    status: TopicStatusValue = "open"
    result: str | None = None


class BookingState(BaseModel):
    """The workflow's mutable execution state for one booking."""

    booking_id: str
    client_token: str
    hotel: HotelContactData
    booking_ref: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    guests: list[str] = Field(default_factory=list)
    room_type: str | None = None
    language: str = "en"
    wishes: list[str] = Field(default_factory=list)
    topics: list[TopicData] = Field(default_factory=list)
    lifecycle: LifecycleValue = "intake"
    followup_attempts: int = 0
    needs_discovery: bool = False

    def open_topic_ids(self) -> list[str]:
        return [t.topic_id for t in self.topics if t.status == "open"]

    def all_topics_terminal(self) -> bool:
        return bool(self.topics) and all(t.status != "open" for t in self.topics)


class ExtractedData(BaseModel):
    hotel_name: str
    hotel_email: str | None = None
    hotel_website: str | None = None
    booking_ref: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    guests: list[str] = Field(default_factory=list)
    room_type: str | None = None
    wishes: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    missing_required: list[str] = Field(default_factory=list)
    low_confidence: bool = False
    # cover-letter wishes parsed into additional topic labels
    wish_topics: list[str] = Field(default_factory=list)


class ContactResult(BaseModel):
    email: str | None = None
    language: str = "en"
    website: str | None = None
    found: bool = False


class ResolutionData(BaseModel):
    topic_id: str
    status: TopicStatusValue
    result: str = ""


class IntentResult(BaseModel):
    """The agent's decision, flattened to a single serializable object (no Union)."""

    action: ActionValue = "need_more_info"
    to: str | None = None
    subject: str | None = None
    body: str | None = None
    language: str | None = None
    topics: list[str] = Field(default_factory=list)
    step: str | None = None
    resolutions: list[ResolutionData] = Field(default_factory=list)
    reason: str | None = None
    question_to_client: str | None = None


class ForwardInput(BaseModel):
    """A client's forwarded confirmation, passed to start the workflow."""

    client_token: str
    sender_email: str
    subject: str
    cover_text: str
    forwarded_payload: str


class ResumeInput(BaseModel):
    """Continue-As-New handoff payload.

    Instead of re-extracting, the new run restores ``state`` and resumes the negotiation loop with
    the pending ``trigger`` and any signal queue contents that arrived mid-tour ("in-flight"
    signals must survive the history reset).
    """

    state: BookingState
    trigger_kind: str = "compose_initial"
    trigger_body: str = ""
    trigger_subject: str | None = None
    pending_replies: list[tuple[str, str, str | None]] = Field(default_factory=list)
    pending_followups: list[str] = Field(default_factory=list)
    pending_delivery_failures: list[tuple[str, str]] = Field(default_factory=list)


class RunInput(BaseModel):
    """Workflow run entry: exactly one of ``forward`` (fresh booking) or ``resume`` (Continue-As-New
    handoff) is set.

    This wrapper is a single concrete type so the default Temporal data converter round-trips it
    reliably — a top-level ``ForwardInput | ResumeInput`` union is not deserializable by the
    converter (TypeAdapter cannot resolve the string-form union). The union is kept *inside* the
    model, where pydantic resolves it natively.
    """

    forward: ForwardInput | None = None
    resume: ResumeInput | None = None
