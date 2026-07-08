"""Gated Temporal E2E for the hardening change (bounded retry + Continue-As-New).

Requires a Temporal dev server via ``WorkflowEnvironment.start_local()`` (downloaded on first
use). Gated behind ``KKR_E2E_TEMPORAL=1`` so the offline suite stays green.

Run::
    KKR_E2E_TEMPORAL=1 uv run pytest tests/workflows/test_workflow_hardening.py
"""

from __future__ import annotations

import asyncio
import os

import pytest

from domain.enums import TopicStatus
from domain.intents import Resolved, TopicResolution
from infrastructure.persistence.in_memory import InMemoryBookingRepository
from infrastructure.workflows.activities import ConciergeActivities
from infrastructure.workflows.dtos import ForwardInput, RunInput
from infrastructure.workflows.workflow import BookingWorkflow
from tests.workflows.test_activities import (
    FakeDiscoverer,
    FakeExtractor,
    FakeGateway,
    FakeNegotiator,
    FakeNotifier,
    FakeReporter,
    _extracted,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("KKR_E2E_TEMPORAL") != "1",
    reason="set KKR_E2E_TEMPORAL=1 to run Temporal workflow hardening E2E tests",
)

_DEFAULT_ARGS = [60, 2, 14 * 24 * 3600, 30 * 24 * 3600, 5]
# run() positional tail: reply_timeout=60s, followup_max=2, clarify=14d, reactivation=30d, threshold=5


class _ServerEnv:
    """Minimal WorkflowEnvironment-like shim over an external server: provides ``client`` and a
    ``new_worker`` backed by a real :class:`temporalio.worker.Worker`` (the from_client env does
    not host workers)."""

    def __init__(self, client):  # type: ignore[no-untyped-def]
        self.client = client

    def new_worker(self, task_queue: str, **kwargs):  # type: ignore[no-untyped-def]
        from temporalio.worker import Worker

        return Worker(self.client, task_queue=task_queue, **kwargs)

    async def __aenter__(self):  # type: ignore[no-untyped-def]
        return self

    async def __aexit__(self, *exc):  # type: ignore[no-untyped-def]
        return False


async def _workflow_env():  # type: ignore[no-untyped-def]
    """Use the existing Temporal server at ``KKR_E2E_TEMPORAL_TARGET`` if set (e.g. the docker
    compose stack), otherwise fall back to a freshly-downloaded dev server."""
    from temporalio.testing import WorkflowEnvironment

    target = os.environ.get("KKR_E2E_TEMPORAL_TARGET")
    if target:
        from temporalio.client import Client

        return _ServerEnv(await Client.connect(target))
    return await WorkflowEnvironment.start_local()


def _forward() -> ForwardInput:
    return ForwardInput(
        client_token="tok",
        sender_email="c@x.com",
        subject="Fwd",
        cover_text="",
        forwarded_payload="conf",
    )


def _registered(activities: ConciergeActivities):  # type: ignore[no-untyped-def]
    """Bound @activity.defn methods, mirroring build_worker (see hardening G1)."""
    return [
        activities.extract,
        activities.discover_contact,
        activities.agent_turn,
        activities.send_email,
        activities.build_report,
        activities.relay_to_client,
        activities.update_booking_state,
        activities.record_inbound_reply,
    ]


@pytest.mark.asyncio
async def test_llm_activity_retry_is_bounded() -> None:
    """An always-failing LLM activity retries a bounded number of times (LLM_RETRY_POLICY, max 3),
    then the workflow run fails — it never loops forever on a down provider."""
    class CountingExtractor:
        def __init__(self) -> None:
            self.calls = 0

        async def extract(self, event):  # type: ignore[no-untyped-def]
            self.calls += 1
            raise RuntimeError("provider down")

    async with await _workflow_env() as env:
        extractor = CountingExtractor()
        activities = ConciergeActivities(
            extractor=extractor,  # type: ignore[arg-type]
            discoverer=FakeDiscoverer("stay@grand.com"),
            negotiator=FakeNegotiator(Resolved(resolutions=[])),
            reporter=FakeReporter(),
            gateway=FakeGateway(),
            notifier=FakeNotifier(),
            bookings=InMemoryBookingRepository(),
            mail_domain="kkr-hotel.com",
        )
        async with env.new_worker("kkr-tasks", workflows=[BookingWorkflow], activities=_registered(activities)):
            handle = await env.client.start_workflow(
                BookingWorkflow.run,
                args=[RunInput(forward=_forward()), *_DEFAULT_ARGS],
                id="bounded-retry",
                task_queue="kkr-tasks",
            )
            with pytest.raises(Exception):  # noqa: B017 - Temporal surfaces a wrapped failure of any kind
                await handle.result()
        assert extractor.calls == 3, f"LLM activity should retry exactly 3 times, got {extractor.calls}"


@pytest.mark.asyncio
async def test_continue_as_new_transfers_state_and_resumes() -> None:
    """With continue_as_new_threshold=2, a negotiation needing 3 agent-turns must continue-as-new
    once and resume in a fresh run, carrying BookingState (incl. topic ids) so the 3rd turn can
    resolve. Report is delivered iff state transfer worked; the negotiator is called exactly 3
    times iff resume (not re-extract) happened."""
    class StatefulNegotiator:
        """Empty Resolved for calls < resolve_at (keeps topics open), full resolve at resolve_at."""

        def __init__(self, resolve_at: int) -> None:
            self.calls = 0
            self._resolve_at = resolve_at

        async def turn(self, booking_id, trigger, booking):  # type: ignore[no-untyped-def]
            self.calls += 1
            if self.calls >= self._resolve_at:
                return Resolved(
                    resolutions=[
                        TopicResolution(topic_id=t.topic_id, status=TopicStatus.RESOLVED, result="ok")
                        for t in booking.topics
                    ]
                )
            return Resolved(resolutions=[])

    async with await _workflow_env() as env:
        notifier = FakeNotifier()
        negotiator = StatefulNegotiator(resolve_at=3)
        activities = ConciergeActivities(
            extractor=FakeExtractor(_extracted()),
            discoverer=FakeDiscoverer("stay@grand.com"),
            negotiator=negotiator,  # type: ignore[arg-type]
            reporter=FakeReporter(),
            gateway=FakeGateway(),
            notifier=notifier,
            bookings=InMemoryBookingRepository(),
            mail_domain="kkr-hotel.com",
        )
        async with env.new_worker("kkr-tasks", workflows=[BookingWorkflow], activities=_registered(activities)):
            handle = await env.client.start_workflow(
                BookingWorkflow.run,
                args=[
                    RunInput(forward=_forward()),
                    60,  # reply_timeout
                    2,  # followup_max
                    14 * 24 * 3600,  # clarify
                    30 * 24 * 3600,  # reactivation
                    2,  # continue_as_new_threshold — force a handoff before turn 3
                ],
                id="continue-as-new",
                task_queue="kkr-tasks",
            )
            # The 3rd turn resolves → report delivered. Poll, then terminate the long-lived wait.
            for _ in range(200):
                if any("report" in s.lower() for s, _ in notifier.notified):
                    break
                await asyncio.sleep(0.1)
            await handle.terminate()
        assert any("report" in s.lower() for s, _ in notifier.notified), "report not delivered after continue-as-new"
        assert negotiator.calls == 3, (
            f"expected 3 agent-turns across 2 runs (1 continue-as-new), got {negotiator.calls}"
        )
