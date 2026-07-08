"""Domain identifiers and address-routing primitives.

Kept pure (stdlib only): ``domain`` depends on nothing external.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# --- NewTypes: raw, validated string identifiers ---------------------------------

BookingId = str  # workflow_id == thread_id == booking_id == local-part for b.<booking>
ClientToken = str
TopicId = str
MessageId = str


# --- Validated value objects ------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_LOCAL_RE = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class EmailAddress:
    """A normalized, lowercased email address."""

    value: str

    def __post_init__(self) -> None:
        cleaned = self.value.strip().lower()
        if not _EMAIL_RE.match(cleaned):
            raise ValueError(f"invalid email address: {self.value!r}")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class LocalPart:
    """The local part of an inbound address on the catch-all domain.

    Dispatched by the inbound router: ``c.<token>`` → intake, ``b.<booking>`` → conversation.
    """

    value: str

    def __post_init__(self) -> None:
        cleaned = self.value.strip().lower()
        if not cleaned or not _LOCAL_RE.match(cleaned):
            raise ValueError(f"invalid local-part: {self.value!r}")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


# --- Inbound routing --------------------------------------------------------------

RouteKind = Literal["intake", "conversation", "unknown"]
INTAKE_PREFIX = "c."
CONVERSATION_PREFIX = "b."


@dataclass(frozen=True)
class AddressRoute:
    """Result of dispatching an inbound local-part."""

    kind: RouteKind
    token: ClientToken | None = None
    booking_id: BookingId | None = None

    @property
    def is_intake(self) -> bool:
        return self.kind == "intake"

    @property
    def is_conversation(self) -> bool:
        return self.kind == "conversation"


def route(local_part: str) -> AddressRoute:
    """Dispatch an inbound local-part into an :class:`AddressRoute`.

    >>> route("c.abc123").is_intake
    True
    >>> route("b.42").booking_id
    '42'
    """
    cleaned = local_part.strip().lower()
    if cleaned.startswith(INTAKE_PREFIX) and len(cleaned) > len(INTAKE_PREFIX):
        return AddressRoute(kind="intake", token=cleaned[len(INTAKE_PREFIX):])
    if cleaned.startswith(CONVERSATION_PREFIX) and len(cleaned) > len(CONVERSATION_PREFIX):
        return AddressRoute(kind="conversation", booking_id=cleaned[len(CONVERSATION_PREFIX):])
    return AddressRoute(kind="unknown")


def intake_address(token: ClientToken, domain: str) -> EmailAddress:
    """The per-client intake address: ``c.<token>@<domain>``."""
    if not token:
        raise ValueError("client token must not be empty")
    return EmailAddress(f"{INTAKE_PREFIX}{token}@{domain}")


def conversation_address(booking_id: BookingId, domain: str) -> EmailAddress:
    """The booking-scoped conversation / Reply-To address: ``b.<booking>@<domain>``."""
    if not booking_id:
        raise ValueError("booking id must not be empty")
    return EmailAddress(f"{CONVERSATION_PREFIX}{booking_id}@{domain}")
