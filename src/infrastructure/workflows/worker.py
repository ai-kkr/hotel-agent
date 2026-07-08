"""Temporal worker setup (spec 6.1).

Builds a client against the configured Temporal target and runs a worker that registers the
``BookingWorkflow`` and the ``ConciergeActivities`` on the configured task queue.
"""

from __future__ import annotations

from temporalio.client import Client
from temporalio.worker import Worker

from infrastructure.config import Settings
from infrastructure.workflows.activities import ConciergeActivities
from infrastructure.workflows.workflow import BookingWorkflow


async def build_client(settings: Settings) -> Client:
    """Connect a Temporal client to the configured target."""
    return await Client.connect(settings.temporal_target)


def build_worker(client: Client, settings: Settings, activities: ConciergeActivities) -> Worker:
    """Create (but do not start) a worker with the workflow + activities registered.

    Activities must be registered as their bound ``@activity.defn`` methods, **not** as the
    instance: temporalio calls ``_Definition.must_from_callable`` on each list element and does
    not auto-discover methods from a class instance, so passing ``[activities]`` raises
    ``TypeError: Activity <unknown> missing attributes``.
    """
    return Worker(
        client=client,
        task_queue=settings.temporal_task_queue,
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
    )


async def run_worker(client: Client, settings: Settings, activities: ConciergeActivities) -> None:
    """Run the worker until interrupted."""
    worker = build_worker(client, settings, activities)
    await worker.run()
