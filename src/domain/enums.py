"""Domain enums and lifecycle values."""

from __future__ import annotations

from enum import StrEnum


class TopicStatus(StrEnum):
    """Per-topic negotiation outcome."""

    OPEN = "open"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    CANT_PROGRESS = "cant_progress"


class BookingLifecycle(StrEnum):
    """Where a booking sits in its durable conversation lifecycle.

    Mirrors the lifecycle in ``design.md``:
    INTAKE → EXTRACTED → CONTACT_READY → IN_CONVERSATION ⇄ AWAITING_REPLY →
    TOPICS_RESOLVED → REPORT_SENT → AWAITING_CLIENT_FOLLOWUP → (reactivation).
    """

    INTAKE = "intake"
    EXTRACTED = "extracted"
    CONTACT_READY = "contact_ready"
    IN_CONVERSATION = "in_conversation"
    AWAITING_REPLY = "awaiting_reply"
    TOPICS_RESOLVED = "topics_resolved"
    REPORT_SENT = "report_sent"
    AWAITING_CLIENT_FOLLOWUP = "awaiting_client_followup"
    CANT_PROGRESS = "cant_progress"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Channel(StrEnum):
    """Client-facing channels. Email on v1; others are adapter slots."""

    EMAIL = "email"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    NATIVE_APP = "native_app"
    API = "api"


class SenderRole(StrEnum):
    CLIENT = "client"
    HOTEL = "hotel"
    SYSTEM = "system"


# Default topic labels initialized at intake.
TOPIC_EARLY_CHECKIN = "early-checkin"
TOPIC_ROOM_UPGRADE = "room-upgrade"
DEFAULT_TOPIC_LABELS: tuple[str, ...] = (TOPIC_EARLY_CHECKIN, TOPIC_ROOM_UPGRADE)
