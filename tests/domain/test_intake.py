from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.application import IntakeService
from domain.entities import Client
from domain.errors import UnauthorizedSender, UnknownClientToken
from domain.events import ConfirmForward
from domain.ids import EmailAddress
from infrastructure.persistence.in_memory import InMemoryClientRepository


class RecordingGateway:
    def __init__(self) -> None:
        self.started: list[ConfirmForward] = []

    async def start_booking(self, event: ConfirmForward) -> None:
        self.started.append(event)

    async def signal_hotel_reply(self, event: object) -> None: ...
    async def signal_client_message(self, event: object) -> None: ...
    async def signal_delivery_failure(self, *args: object) -> None: ...


def _forward(token: str, sender: str) -> ConfirmForward:
    return ConfirmForward(
        client_token=token,
        sender_email=EmailAddress(sender),
        subject="Fwd: booking",
        cover_text="",
        forwarded_payload="confirmation body",
        received_at=datetime.now(tz=UTC),
    )


@pytest.fixture
def setup() -> tuple[IntakeService, RecordingGateway, InMemoryClientRepository]:
    clients = InMemoryClientRepository()
    gateway = RecordingGateway()
    intake = IntakeService(clients=clients, gateway=gateway)
    return intake, gateway, clients


class TestIntake:
    async def test_valid_forward_starts_booking(self, setup: tuple) -> None:
        intake, gateway, clients = setup
        await clients.add(Client(token="tok", email=EmailAddress("client@example.com")))
        await intake.handle(_forward("tok", "client@example.com"))
        assert len(gateway.started) == 1

    async def test_unknown_token_rejected(self, setup: tuple) -> None:
        intake, _gateway, _clients = setup
        with pytest.raises(UnknownClientToken):
            await intake.handle(_forward("nope", "client@example.com"))

    async def test_sender_mismatch_rejected(self, setup: tuple) -> None:
        intake, _gateway, clients = setup
        await clients.add(Client(token="tok", email=EmailAddress("client@example.com")))
        with pytest.raises(UnauthorizedSender):
            await intake.handle(_forward("tok", "attacker@evil.com"))

    async def test_rejected_does_not_start(self, setup: tuple) -> None:
        intake, gateway, _clients = setup
        with pytest.raises(UnknownClientToken):
            await intake.handle(_forward("nope", "x@y.com"))
        assert gateway.started == []
