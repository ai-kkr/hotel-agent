"""Agent intents: the agent produces these; the workflow executes side-effects.

By design (D3) the agent has **no** ``send_email`` tool. It emits a structured intent and the
workflow applies it through activities. This keeps the agent replay-safe and side-effect free.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.enums import TopicStatus
from domain.ids import EmailAddress, TopicId


@dataclass(frozen=True)
class TopicResolution:
    """How a single topic ended after the agent parsed a hotel reply."""

    topic_id: TopicId
    status: TopicStatus
    result: str

    def __post_init__(self) -> None:
        if self.status == TopicStatus.RESOLVED and not self.result.strip():
            raise ValueError("a resolved topic must carry a non-empty result")


@dataclass(frozen=True)
class SendEmail:
    """Agent decided to send (or re-send) an email to the hotel."""

    to: EmailAddress
    subject: str
    body: str
    language: str
    topic_ids: list[TopicId]
    step: str  # idempotency step label, e.g. "initial", "followup1", "clarify"

    def __post_init__(self) -> None:
        if not self.subject.strip() or not self.body.strip():
            raise ValueError("email subject and body must not be empty")
        if not self.step.strip():
            raise ValueError("email step (idempotency key suffix) must not be empty")


@dataclass(frozen=True)
class NeedMoreInfo:
    """Agent cannot proceed without more information from the client."""

    reason: str
    question_to_client: str


@dataclass(frozen=True)
class Resolved:
    """Agent resolved topics (full or partial) from a hotel reply."""

    resolutions: list[TopicResolution] = field(default_factory=list)


@dataclass(frozen=True)
class SearchDone:
    """Result of contact/language discovery."""

    hotel_name: str
    language: str = "en"  # resolved correspondence language; defaults to English
    email: EmailAddress | None = None
    website: str | None = None
    found: bool = True  # False when no contact could be found → CAN'T_PROGRESS

    def __post_init__(self) -> None:
        if not self.hotel_name.strip():
            raise ValueError("hotel_name must not be empty")


AgentIntent = SendEmail | NeedMoreInfo | Resolved | SearchDone


# --- Triggers: what kicks a negotiation turn ----------------------------------------

@dataclass(frozen=True)
class ComposeInitial:
    """Compose the first (batched) email to the hotel."""


@dataclass(frozen=True)
class ParseHotelReply:
    """Parse a hotel reply and decide next steps."""

    body: str
    subject: str | None = None


@dataclass(frozen=True)
class ClientFollowup:
    """A client follow-up arrived after a report (may reopen / add topics)."""

    body: str


@dataclass(frozen=True)
class TimeoutFollowup:
    """The reply timeout elapsed with no answer."""


Trigger = ComposeInitial | ParseHotelReply | ClientFollowup | TimeoutFollowup
