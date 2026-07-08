from __future__ import annotations

import httpx
from httpx import ASGITransport

from domain.application import MailboxService
from domain.enums import Channel
from infrastructure.config import Settings
from infrastructure.persistence.in_memory import (
    InMemoryChannelSessionRepository,
    InMemoryClientRepository,
)
from presentation.app import create_app
from presentation.container import build_webhook_deps


class _NullNormalizer:
    def parse(self, payload):  # type: ignore[no-untyped-def]
        raise AssertionError("mailbox endpoint must not invoke the mail normalizer")


async def _make_app(
    *, bot_secret: str
) -> tuple[httpx.AsyncClient, MailboxService]:
    clients = InMemoryClientRepository()
    sessions = InMemoryChannelSessionRepository()
    mailbox = MailboxService(
        clients=clients, sessions=sessions, mail_domain="kkr-hotel.com", token_factory=lambda: "tok"
    )
    settings = Settings(
        mail_provider="stub",
        mail_domain="kkr-hotel.com",
        mailgun_signing_key="",
        bot_api_secret=bot_secret,
    )
    deps = build_webhook_deps(
        settings=settings,
        normalizer=_NullNormalizer(),  # type: ignore[arg-type]
        dispatcher=None,  # type: ignore[arg-type]
        gateway=None,  # type: ignore[arg-type]
        intake=None,  # type: ignore[arg-type]
        mailbox=mailbox,
    )
    app = create_app(webhook_deps=deps)
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test"), mailbox


class TestClientMailboxEndpoint:
    async def test_creates_client_with_valid_secret(self) -> None:
        client, mailbox = await _make_app(bot_secret="s3cret")
        async with client:
            resp = await client.post(
                "/api/client-mailbox",
                json={"channel": "telegram", "address": "chat:1"},
                headers={"x-bot-secret": "s3cret"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["mailbox"] == "c.tok@kkr-hotel.com"
        resolved = await mailbox.resolve_or_create(Channel.TELEGRAM, "chat:1")
        assert resolved.value == body["mailbox"]

    async def test_bearer_secret_accepted(self) -> None:
        client, _mailbox = await _make_app(bot_secret="s3cret")
        async with client:
            resp = await client.post(
                "/api/client-mailbox",
                json={"channel": "telegram", "address": "chat:2"},
                headers={"authorization": "Bearer s3cret"},
            )
        assert resp.status_code == 200

    async def test_wrong_secret_rejected(self) -> None:
        client, _mailbox = await _make_app(bot_secret="s3cret")
        async with client:
            resp = await client.post(
                "/api/client-mailbox",
                json={"channel": "telegram", "address": "chat:3"},
                headers={"x-bot-secret": "wrong"},
            )
        assert resp.status_code == 401

    async def test_missing_secret_rejected(self) -> None:
        client, _mailbox = await _make_app(bot_secret="s3cret")
        async with client:
            resp = await client.post(
                "/api/client-mailbox",
                json={"channel": "telegram", "address": "chat:4"},
            )
        assert resp.status_code == 401

    async def test_secret_not_configured(self) -> None:
        client, _mailbox = await _make_app(bot_secret="")
        async with client:
            resp = await client.post(
                "/api/client-mailbox",
                json={"channel": "telegram", "address": "chat:5"},
                headers={"x-bot-secret": "anything"},
            )
        assert resp.status_code == 503
