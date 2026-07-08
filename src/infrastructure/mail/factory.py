"""Adapter factory: selects mail provider adapters by configuration (design D8 / spec 4.5).

Adding a provider is a config switch + a new adapter module; the rest of the system is unchanged.
"""

from __future__ import annotations

from domain.ports import BookingRepository, InboundMailNormalizer, OutboundMailGateway
from infrastructure.config import Settings
from infrastructure.mail.mailgun import MailgunOutboundGateway, MailgunWebhookNormalizer
from infrastructure.mail.stub import StubInboundNormalizer, StubOutboundGateway
from infrastructure.persistence.in_memory import InMemoryBookingRepository


def build_inbound_normalizer(settings: Settings) -> InboundMailNormalizer:
    """Build the inbound normalizer for the configured provider."""
    match settings.mail_provider:
        case "mailgun":
            return MailgunWebhookNormalizer()
        case "stub":
            return StubInboundNormalizer()
        case "custom":
            raise NotImplementedError("custom inbound normalizer adapter not yet implemented")
        case _:
            raise ValueError(f"unknown mail_provider: {settings.mail_provider!r}")


def build_outbound_gateway(
    settings: Settings, repo: BookingRepository | None = None
) -> OutboundMailGateway:
    """Build the outbound gateway for the configured provider.

    ``repo`` records outbound messages for idempotency; defaults to an in-memory store when none is
    provided (the real deployment passes a SqlAlchemy repository).
    """
    match settings.mail_provider:
        case "mailgun":
            return MailgunOutboundGateway(
                api_key=settings.mailgun_api_key,
                base_url=settings.mailgun_base_url,
                mail_domain=settings.mail_domain,
                repo=repo or InMemoryBookingRepository(),
            )
        case "stub":
            return StubOutboundGateway(
                repo=repo or InMemoryBookingRepository(),
                mail_domain=settings.mail_domain,
            )
        case "custom":
            raise NotImplementedError("custom outbound gateway adapter not yet implemented")
        case _:
            raise ValueError(f"unknown mail_provider: {settings.mail_provider!r}")
