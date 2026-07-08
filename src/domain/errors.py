"""Domain-level errors raised by application services."""

from __future__ import annotations


class IntakeError(Exception):
    """Base class for booking-intake failures."""


class UnknownClientToken(IntakeError):
    """The intake token does not resolve to a registered client."""


class UnauthorizedSender(IntakeError):
    """The sender does not match the client's registered (SPF/DKIM-verified) email."""


class ExtractionInsufficient(IntakeError):
    """Extraction could not confidently produce a usable booking."""


class UnknownChannelSession(IntakeError):
    """A chat-forward arrived from a channel address with no bound ChannelSession."""
