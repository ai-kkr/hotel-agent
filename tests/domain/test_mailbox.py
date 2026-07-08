from __future__ import annotations

import pytest

from domain.application import MailboxService
from domain.enums import Channel
from domain.ids import intake_address
from infrastructure.persistence.in_memory import (
    InMemoryChannelSessionRepository,
    InMemoryClientRepository,
)


def _service(token_seq: list[str]) -> MailboxService:
    clients = InMemoryClientRepository()
    sessions = InMemoryChannelSessionRepository()
    tokens = iter(token_seq)
    return MailboxService(
        clients=clients,
        sessions=sessions,
        mail_domain="kkr-hotel.com",
        token_factory=lambda: next(tokens),
    )


class TestMailbox:
    async def test_first_request_creates_client(self) -> None:
        svc = _service(["token-a"])
        address = await svc.resolve_or_create(Channel.TELEGRAM, "chat:123")
        assert address == intake_address("token-a", "kkr-hotel.com")
        # session bound
        assert await svc.sessions.client_for(Channel.TELEGRAM, "chat:123") == "token-a"
        # client created with the mailbox as its identity anchor
        client = await svc.clients.by_token("token-a")
        assert client is not None
        assert client.email == address

    async def test_repeat_request_is_idempotent(self) -> None:
        svc = _service(["token-a", "token-b"])
        first = await svc.resolve_or_create(Channel.TELEGRAM, "chat:123")
        second = await svc.resolve_or_create(Channel.TELEGRAM, "chat:123")
        assert first == second
        # token_factory must not have been consumed a second time
        assert await svc.clients.by_token("token-b") is None

    async def test_cross_client_isolation(self) -> None:
        svc = _service(["token-a", "token-b"])
        a = await svc.resolve_or_create(Channel.TELEGRAM, "chat:1")
        b = await svc.resolve_or_create(Channel.TELEGRAM, "chat:2")
        assert a != b
        assert await svc.sessions.client_for(Channel.TELEGRAM, "chat:1") == "token-a"
        assert await svc.sessions.client_for(Channel.TELEGRAM, "chat:2") == "token-b"

    async def test_address_collision_rejected(self) -> None:
        svc = _service(["token-a", "token-b"])
        await svc.resolve_or_create(Channel.TELEGRAM, "chat:1")
        # binding the same chat to a different client must fail (address is globally unique)
        sessions = svc.sessions
        from domain.entities import ChannelSession

        with pytest.raises(ValueError):
            await sessions.upsert(
                ChannelSession(client_token="token-b", channel=Channel.TELEGRAM, address="chat:1")
            )
