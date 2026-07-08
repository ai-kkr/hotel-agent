from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.application import ChatIntakeService, IntakeService
from domain.entities import ChannelSession, Client
from domain.enums import Channel
from domain.errors import UnauthorizedSender
from domain.events import ChatForward, ConfirmForward
from domain.ids import EmailAddress, intake_address
from infrastructure.persistence.in_memory import (
    InMemoryChannelSessionRepository,
    InMemoryClientRepository,
)


class RecordingGateway:
    def __init__(self) -> None:
        self.started: list[ConfirmForward] = []

    async def start_booking(self, event: ConfirmForward) -> None:
        self.started.append(event)

    async def signal_hotel_reply(self, event: object) -> None: ...
    async def signal_client_message(self, event: object) -> None: ...
    async def signal_delivery_failure(self, *args: object) -> None: ...


@pytest.fixture
def setup() -> tuple[ChatIntakeService, IntakeService, RecordingGateway, InMemoryClientRepository, InMemoryChannelSessionRepository]:
    clients = InMemoryClientRepository()
    sessions = InMemoryChannelSessionRepository()
    gateway = RecordingGateway()
    chat_intake = ChatIntakeService(sessions=sessions, clients=clients, gateway=gateway)
    email_intake = IntakeService(clients=clients, gateway=gateway)
    return chat_intake, email_intake, gateway, clients, sessions


class TestChatIntake:
    async def test_known_session_starts_booking(self, setup: tuple) -> None:
        chat_intake, _email, gateway, clients, sessions = setup
        await clients.add(Client(token="tok", email=intake_address("tok", "kkr-hotel.com")))
        await sessions.upsert(
            ChannelSession(client_token="tok", channel=Channel.TELEGRAM, address="chat:1")
        )
        outcome = await chat_intake.handle(
            ChatForward(
                client_token="",  # ignored; resolved from session
                chat_id="chat:1",
                cover_text="please early check-in",
                forwarded_payload="confirmation body",
                received_at=datetime.now(tz=UTC),
            )
        )
        assert outcome.started is True
        assert outcome.client_token == "tok"
        assert len(gateway.started) == 1
        assert gateway.started[0].client_token == "tok"
        assert gateway.started[0].forwarded_payload == "confirmation body"
        assert gateway.started[0].cover_text == "please early check-in"

    async def test_unknown_session_does_not_start(self, setup: tuple) -> None:
        chat_intake, _email, gateway, _clients, _sessions = setup
        outcome = await chat_intake.handle(
            ChatForward(
                client_token="",
                chat_id="unknown-chat",
                cover_text="",
                forwarded_payload="confirmation body",
                received_at=datetime.now(tz=UTC),
            )
        )
        assert outcome.started is False
        assert outcome.needs_mailbox is True
        assert gateway.started == []

    async def test_chat_and_email_produce_equivalent_forward(self, setup: tuple) -> None:
        chat_intake, email_intake, gateway, clients, sessions = setup
        mailbox = intake_address("tok", "kkr-hotel.com")
        await clients.add(Client(token="tok", email=mailbox))
        await sessions.upsert(
            ChannelSession(client_token="tok", channel=Channel.TELEGRAM, address="chat:1")
        )

        await chat_intake.handle(
            ChatForward(
                client_token="",
                chat_id="chat:1",
                cover_text="wishes",
                forwarded_payload="confirmation body",
                received_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        await email_intake.handle(
            ConfirmForward(
                client_token="tok",
                sender_email=mailbox,
                subject="Fwd: booking",
                cover_text="wishes",
                forwarded_payload="confirmation body",
                received_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        # Both paths produce an equivalent forward to start_booking (same token, payload, wishes).
        assert {f.client_token for f in gateway.started} == {"tok"}
        assert all(f.forwarded_payload == "confirmation body" for f in gateway.started)
        assert all(f.cover_text == "wishes" for f in gateway.started)
        assert len(gateway.started) == 2

    async def test_email_path_keeps_strict_sender_auth(self, setup: tuple) -> None:
        _chat, email_intake, gateway, clients, _sessions = setup
        await clients.add(Client(token="tok", email=EmailAddress("client@example.com")))
        with pytest.raises(UnauthorizedSender):
            await email_intake.handle(
                ConfirmForward(
                    client_token="tok",
                    sender_email=EmailAddress("attacker@evil.com"),
                    subject="Fwd: booking",
                    cover_text="",
                    forwarded_payload="confirmation body",
                    received_at=datetime.now(tz=UTC),
                )
            )
        assert gateway.started == []
