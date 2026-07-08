"""Temporal-backed :class:`domain.ports.WorkflowGateway` (spec 6.7 wiring).

The presentation layer (webhooks) calls this to start/signals booking workflows. It depends on a
Temporal client, never on workflow internals, so HTTP stays thin and testable with a fake gateway.
"""

from __future__ import annotations

import uuid
from contextlib import suppress

from temporalio.client import Client

from domain.events import ClientMessage, ConfirmForward, HotelReply
from domain.ids import BookingId
from infrastructure.workflows.dtos import ForwardInput, RunInput
from infrastructure.workflows.workflow import BookingWorkflow


class TemporalWorkflowGateway:
    """Implements :class:`domain.ports.WorkflowGateway` over a Temporal client."""

    def __init__(
        self,
        client: Client,
        task_queue: str,
        *,
        reply_timeout_seconds: int,
        followup_max: int,
        clarify_timeout_seconds: int,
        reactivation_timeout_seconds: int,
        continue_as_new_threshold: int,
    ) -> None:
        self._client = client
        self._task_queue = task_queue
        self._reply_timeout_seconds = reply_timeout_seconds
        self._followup_max = followup_max
        self._clarify_timeout_seconds = clarify_timeout_seconds
        self._reactivation_timeout_seconds = reactivation_timeout_seconds
        self._continue_as_new_threshold = continue_as_new_threshold

    async def start_booking(self, event: ConfirmForward) -> None:
        booking_id = _new_booking_id()
        forward = ForwardInput(
            client_token=event.client_token,
            sender_email=event.sender_email.value,
            subject=event.subject,
            cover_text=event.cover_text,
            forwarded_payload=event.forwarded_payload,
        )
        await self._client.start_workflow(
            BookingWorkflow.run,
            args=[
                RunInput(forward=forward),
                self._reply_timeout_seconds,
                self._followup_max,
                self._clarify_timeout_seconds,
                self._reactivation_timeout_seconds,
                self._continue_as_new_threshold,
            ],
            id=booking_id,
            task_queue=self._task_queue,
        )

    async def signal_hotel_reply(self, event: HotelReply) -> None:
        handle = self._client.get_workflow_handle(event.booking_id)
        await handle.signal(
            BookingWorkflow.on_hotel_reply,
            args=[event.from_email.value, event.body, event.subject],
        )

    async def signal_client_message(self, event: ClientMessage) -> None:
        if event.booking_id is None:
            return
        handle = self._client.get_workflow_handle(event.booking_id)
        await handle.signal(BookingWorkflow.client_followup, args=[event.body])

    async def signal_delivery_failure(
        self, booking_id: BookingId, severity: str, description: str
    ) -> None:
        handle = self._client.get_workflow_handle(booking_id)
        await handle.signal(BookingWorkflow.delivery_failure, args=[severity, description])

    async def cancel_booking(self, booking_id: BookingId) -> None:
        """Cancel the booking's Temporal workflow (``workflow_id == booking_id``, design D8).

        Best-effort: a workflow that already completed/terminated is treated as already cancelled
        (the caller marks the booking ``CANCELLED`` idempotently regardless).
        """
        handle = self._client.get_workflow_handle(booking_id)
        with suppress(Exception):
            # Already terminated / not running — cancellation is idempotent at the domain level.
            await handle.cancel()


def _new_booking_id() -> str:
    return uuid.uuid4().hex
