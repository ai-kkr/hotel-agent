"""Tests for the local-run assembly (change: local-agent-run-harness, task 5.1)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import infrastructure.db.models  # noqa: F401
from infrastructure.agents.factory import AgentBundle
from infrastructure.config import Settings
from infrastructure.db.base import Base
from infrastructure.mail.stub import StubOutboundGateway
from infrastructure.runtime import build_local_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        mail_provider="stub",
        mail_domain="kkr-hotel.com",
        temporal_target="localhost:7233",
        temporal_task_queue="kkr-hotel",
    )


@pytest.fixture
def agents() -> AgentBundle:
    # The wiring never invokes agents; stand-ins are sufficient.
    return AgentBundle(
        extractor=MagicMock(name="extractor"),
        discoverer=MagicMock(name="discoverer"),
        negotiator=MagicMock(name="negotiator"),
        reporter=MagicMock(name="reporter"),
    )


@pytest.fixture
async def session_maker():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def test_build_local_app_wires_stub_deps(settings, agents, session_maker):
    runtime = build_local_app(
        settings,
        temporal_client=MagicMock(name="temporal_client"),
        agents=agents,
        session_maker=session_maker,
        worker=MagicMock(name="worker"),
    )

    # The outbound gateway is the stub (no Mailgun), exposing the inspectable outbox.
    assert isinstance(runtime.outbox_gateway, StubOutboundGateway)
    # The FastAPI app carries webhook deps built with the stub normalizer.
    assert runtime.app.state.webhook_deps.normalizer.__class__.__name__ == "StubInboundNormalizer"
    assert runtime.app.state.webhook_deps.settings.mail_provider == "stub"
    assert runtime.worker is not None


def test_build_local_app_rejects_non_stub_provider(agents, session_maker):
    prod_settings = Settings(mail_provider="mailgun")
    with pytest.raises(ValueError, match="KKR_MAIL_PROVIDER=stub"):
        build_local_app(
            prod_settings,
            temporal_client=MagicMock(),
            agents=agents,
            session_maker=session_maker,
            worker=MagicMock(),
        )
