"""End-to-end BookingWorkflow integration test (spec 6.8).

Requires a Temporal dev server, which ``WorkflowEnvironment.start_local()`` downloads on first
use. Gated behind ``KKR_E2E_TEMPORAL=1`` so the default offline suite stays green; set the flag
when a Temporal server (or the downloadable dev server) is available.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date

import pytest

from domain.enums import TopicStatus
from domain.extraction import ExtractedBooking
from domain.ids import EmailAddress
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
)

pytestmark = pytest.mark.skipif(
    os.environ.get("KKR_E2E_TEMPORAL") != "1",
    reason="set KKR_E2E_TEMPORAL=1 to run Temporal workflow integration tests",
)


@pytest.mark.asyncio
async def test_workflow_resolves_and_reports() -> None:
    from tests.workflows.test_workflow_hardening import _workflow_env

    async with await _workflow_env() as env:
        notifier = FakeNotifier()
        resolved = Resolved(
            resolutions=[
                TopicResolution(topic_id="wt:t:early-checkin", status=TopicStatus.RESOLVED, result="granted"),
                TopicResolution(topic_id="wt:t:room-upgrade", status=TopicStatus.RESOLVED, result="offered 40 eur"),
            ]
        )
        activities = ConciergeActivities(
            extractor=FakeExtractor(
                ExtractedBooking(
                    hotel_name="Grand",
                    hotel_email=EmailAddress("stay@grand.com"),
                    booking_ref="R1",
                    check_in=date(2026, 2, 1),
                    check_out=date(2026, 2, 4),
                    confidence=0.9,
                )
            ),
            discoverer=FakeDiscoverer("stay@grand.com"),
            negotiator=FakeNegotiator(resolved),
            reporter=FakeReporter(),
            gateway=FakeGateway(),
            notifier=notifier,
            bookings=InMemoryBookingRepository(),
            mail_domain="kkr-hotel.com",
        )
        forward = ForwardInput(
            client_token="tok",
            sender_email="c@x.com",
            subject="Fwd",
            cover_text="",
            forwarded_payload="conf",
        )
        async with env.new_worker(
            "kkr-tasks",
            workflows=[BookingWorkflow],
            activities=[
                activities.extract,
                activities.discover_contact,
                activities.agent_turn,
                activities.send_email,
                activities.build_report,
                activities.relay_to_client,
                activities.update_booking_state,
                activities.record_inbound_reply,
            ],
        ):
            handle = await env.client.start_workflow(
                BookingWorkflow.run,
                args=[RunInput(forward=forward), 60, 2, 14 * 24 * 3600, 30 * 24 * 3600, 5],
                id="wt",
                task_queue="kkr-tasks",
            )
            # The negotiator resolves both topics immediately, so the workflow should reach the
            # report stage. Poll for the report, then terminate the long-lived reactivation wait.
            for _ in range(100):
                if any("report" in s.lower() for s, _ in notifier.notified):
                    break
                await asyncio.sleep(0.1)
            await handle.terminate()
        assert any("report" in s.lower() for s, _ in notifier.notified), "report not delivered"
