"""Unit tests for BookingWorkflow pieces that don't need a live Temporal server.

The full run-loop (signals/timers/activities) is exercised by the gated E2E test
(``test_workflow_integration.py``). These tests cover the routing state and pure helpers that
CAN run without a workflow context.
"""

from __future__ import annotations

import pytest

from infrastructure.workflows.workflow import BookingWorkflow, PendingEvent, _topics_from_text


@pytest.fixture
def workflow() -> BookingWorkflow:
    return BookingWorkflow()


class TestSignalsAndRouting:
    async def test_init_empty(self, workflow: BookingWorkflow) -> None:
        assert workflow._has_event() is False

    async def test_hotel_reply_signal_queues(self, workflow: BookingWorkflow) -> None:
        await workflow.on_hotel_reply("hotel@grand.com", "Yes", "Re:")
        assert workflow._has_event() is True
        assert workflow._hotel_replies[0] == ("hotel@grand.com", "Yes", "Re:")

    async def test_client_followup_signal_queues(self, workflow: BookingWorkflow) -> None:
        await workflow.client_followup("also ask late checkout")
        assert list(workflow._client_followups) == ["also ask late checkout"]
        assert workflow._has_event() is True

    async def test_delivery_failure_signal_queues(self, workflow: BookingWorkflow) -> None:
        await workflow.delivery_failure("permanent", "user unknown")
        assert workflow._delivery_failures[0] == ("permanent", "user unknown")

    async def test_has_event_false_after_only_empty(self, workflow: BookingWorkflow) -> None:
        assert workflow._has_event() is False


class TestTopicsFromText:
    def test_lines_become_topics(self) -> None:
        assert _topics_from_text("Late checkout\nHigh floor") == ["late checkout", "high floor"]

    def test_ignores_blank_lines(self) -> None:
        assert _topics_from_text("a\n\n  \nb") == ["a", "b"]


class TestPendingEvent:
    def test_defaults(self) -> None:
        e = PendingEvent(kind="timeout")
        assert e.kind == "timeout"
        assert e.body == "" and e.from_email is None
