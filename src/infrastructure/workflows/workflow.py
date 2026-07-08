"""BookingWorkflow (spec 6.3-6.6) - the durable spine.

One workflow per booking (``workflow_id = booking_id``). It owns the conversation lifecycle and
exchanges DTOs with activities. All LLM calls and side-effects happen inside activities (D2); the
workflow only orchestrates signals, timers, and the decision reducers.

Signals: ``on_hotel_reply``, ``client_followup``, ``delivery_failure``.

Versioning contract (design D4)
-------------------------------
Every change to the *structure of commands* this workflow emits — adding/removing an activity
call, reordering orchestration, adding a branch in ``_negotiate`` — is a replay-breaking change
for already-running long-lived workflows. Such a change MUST be gated behind a marker so old
histories replay under the old logic and fresh runs use the new one::

    if workflow.patched("add-x-feature"):
        # new code path
    else:
        # previous code path (kept until no running workflow predates the change)

There are no active patches today; this is the contract any future change must follow.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from infrastructure.workflows import decisions as d
from infrastructure.workflows.activities import ConciergeActivities
from infrastructure.workflows.dtos import (
    BookingState,
    ContactResult,
    ForwardInput,
    IntentResult,
    ResumeInput,
    RunInput,
)

# --- Activity timeouts ---
ACTIVITY_TIMEOUT = timedelta(seconds=120)  # side-effect activities
LLM_ACTIVITY_TIMEOUT = timedelta(seconds=180)  # extract, agent_turn

# --- Retry policies (replace Temporal's default infinite retry) ---
# LLM calls: few attempts, cheap backoff — never loop forever on a down provider.
LLM_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=3,
)
# Discovery (web search / fetch): external and costly — cap attempts.
DISCOVERY_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=3,
)
# Side-effect activities are idempotent (send_email dedups by key, persistence is upsert) so a few
# retries ride out transient DB/mail outages, then fail loudly instead of hanging forever.
SIDE_EFFECT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=5,
)

REPORT_SUBJECT = "Your hotel concierge report"
NEED_INFO_SUBJECT = "We need a bit more information"

# Patch marker for progress-push (design D7 / task 7.1). New runs emit user-visible progress
# notifications; pre-patch histories replay under the old (report-only) behavior. Per the workflow
# versioning contract above, any new activity call MUST be gated like this.
PROGRESS_PUSH_PATCH = "progress-push"

PROGRESS_SUBJECTS = {
    "contact_ready": "We're ready to contact the hotel",
    "sent": "Message sent to the hotel",
    "hotel_replied": "The hotel replied",
}


@dataclass
class PendingEvent:
    """A discrete event popped from the signal queues (timeout / reply / followup / delivery)."""

    kind: str
    from_email: str | None = None
    body: str = ""
    subject: str | None = None
    severity: str | None = None
    description: str | None = None


@workflow.defn(name="BookingWorkflow")
class BookingWorkflow:
    """Durable per-booking negotiation."""

    def __init__(self) -> None:
        self._state: BookingState | None = None
        self._hotel_replies: deque[tuple[str, str, str | None]] = deque()
        self._client_followups: deque[str] = deque()
        self._delivery_failures: deque[tuple[str, str]] = deque()
        # Negotiation agent-turns executed in THIS run. Instance-local so it naturally resets on
        # Continue-As-New (a new run = a new workflow instance); this is the Continue-As-New
        # threshold counter (design D3). NOT stored in BookingState, which would survive the
        # handoff and re-trigger the threshold immediately → infinite continue-as-new loop.
        self._negotiation_runs = 0

    # --- signals (6.4, 6.6) ---

    @workflow.signal
    async def on_hotel_reply(self, from_email: str, body: str, subject: str | None = None) -> None:
        self._hotel_replies.append((from_email, body, subject))

    @workflow.signal
    async def client_followup(self, body: str) -> None:
        self._client_followups.append(body)

    @workflow.signal
    async def delivery_failure(self, severity: str, description: str) -> None:
        self._delivery_failures.append((severity, description))

    def _has_event(self) -> bool:
        return bool(self._hotel_replies or self._client_followups or self._delivery_failures)

    # --- main loop (6.3) ---

    @workflow.run
    async def run(  # pragma: no cover - exercised by gated Temporal E2E
        self,
        start: RunInput,
        reply_timeout_seconds: int = 2 * 24 * 3600,
        followup_max: int = 2,
        clarify_timeout_seconds: int = 14 * 24 * 3600,
        reactivation_timeout_seconds: int = 30 * 24 * 3600,
        continue_as_new_threshold: int = 5,
    ) -> None:
        # Resume from a Continue-As-New handoff, or start fresh from an extracted forward.
        if start.resume is not None:
            resume = start.resume
            state = resume.state
            trigger: tuple[str, str, str | None] | None = (
                resume.trigger_kind,
                resume.trigger_body,
                resume.trigger_subject,
            )
            # Restore "in-flight" signals that arrived during the prior run.
            self._hotel_replies.extend(resume.pending_replies)
            self._client_followups.extend(resume.pending_followups)
            self._delivery_failures.extend(resume.pending_delivery_failures)
        elif start.forward is not None:
            booking_id = workflow.info().workflow_id
            state = await self._extract_and_init(start.forward, booking_id, clarify_timeout_seconds)
            if state is None:
                return  # extraction produced nothing usable and client gave no clarification
            trigger = None
        else:
            return  # malformed start (neither forward nor resume) — nothing to do

        while True:
            # discovery if the confirmation had no hotel contact
            if state.needs_discovery:
                state = await self._do_discovery(state)
                await self._persist(state)
                if state.lifecycle == "cant_progress":
                    await self._finalize(state)
                    state = await self._await_reactivation(state, reactivation_timeout_seconds)
                    if state is None:
                        return
                    trigger = None
                    continue

            # negotiate until topics resolve or progress is impossible (or Continue-As-New fires)
            state, trigger, continued = await self._negotiate(
                state,
                trigger,
                reply_timeout_seconds,
                followup_max,
                clarify_timeout_seconds,
                continue_as_new_threshold,
            )
            if continued:
                return  # workflow.continue_as_new() was issued inside _negotiate

            await self._persist(state)

            # report
            await self._finalize(state)

            # long-lived: wait for a client follow-up, then reactivate (design D11)
            state = await self._await_reactivation(state, reactivation_timeout_seconds)
            if state is None:
                return
            trigger = None

    # --- stages ---

    async def _extract_and_init(self, forward: ForwardInput, booking_id: str, clarify_timeout_seconds: int) -> BookingState | None:  # pragma: no cover - exercised by gated Temporal E2E
        extracted = await workflow.execute_activity(
            ConciergeActivities.extract,
            args=[forward],
            start_to_close_timeout=LLM_ACTIVITY_TIMEOUT,
            retry_policy=LLM_RETRY_POLICY,
        )
        if extracted.low_confidence or extracted.missing_required:
            await workflow.execute_activity(
                ConciergeActivities.relay_to_client,
                args=[booking_id, NEED_INFO_SUBJECT, "Please confirm: " + ", ".join(extracted.missing_required)],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
                retry_policy=SIDE_EFFECT_RETRY_POLICY,
            )
            body = await self._await_followup(reply_timeout_seconds=clarify_timeout_seconds)
            if body is None:
                return None
            # re-extract would need the original payload; for v1 we proceed with what we have.
        return d.state_from_extraction(booking_id, forward.client_token, extracted)

    async def _do_discovery(self, state: BookingState) -> BookingState:  # pragma: no cover - exercised by gated Temporal E2E
        contact: ContactResult = await workflow.execute_activity(
            ConciergeActivities.discover_contact,
            args=[state.hotel.hotel_name, state.hotel.website],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
            retry_policy=DISCOVERY_RETRY_POLICY,
        )
        new_state = d.apply_contact(state, contact)
        if new_state.lifecycle == "contact_ready":
            await self._notify_progress(
                new_state, "contact_ready", f"I found a contact for {new_state.hotel.hotel_name}."
            )
        return new_state

    async def _negotiate(  # pragma: no cover - exercised by gated Temporal E2E
        self,
        state: BookingState,
        trigger: tuple[str, str, str | None] | None,
        reply_timeout_seconds: int,
        followup_max: int,
        clarify_timeout_seconds: int,
        continue_as_new_threshold: int,
    ) -> tuple[BookingState, tuple[str, str, str | None] | None, bool]:
        """Run negotiation turns. Returns (state, next_trigger, continued).

        ``continued`` is True when ``workflow.continue_as_new`` was issued mid-negotiation to bound
        history; the caller must then return.
        """
        if trigger is None:
            trigger_kind, trigger_body, trigger_subject = "compose_initial", "", None
        else:
            trigger_kind, trigger_body, trigger_subject = trigger

        while not (d.should_build_report(state) or state.lifecycle == "cant_progress"):
            # Bound the Event History: after N agent-turns, hand off to a fresh run.
            self._negotiation_runs += 1
            if continue_as_new_threshold > 0 and self._negotiation_runs >= continue_as_new_threshold:
                await self._continue_as_new(
                    state,
                    trigger_kind,
                    trigger_body,
                    trigger_subject,
                    reply_timeout_seconds=reply_timeout_seconds,
                    followup_max=followup_max,
                    clarify_timeout_seconds=clarify_timeout_seconds,
                    reactivation_timeout_seconds=30 * 24 * 3600,
                    continue_as_new_threshold=continue_as_new_threshold,
                )
                return state, (trigger_kind, trigger_body, trigger_subject), True

            intent = await self._agent_turn(state, trigger_kind, trigger_body, trigger_subject)

            match intent.action:
                case "send_email":
                    await self._send_email(state, intent)
                    state = d.record_email_sent(state, intent.step)
                    await self._persist(state)
                    await self._notify_progress(
                        state, "sent", f"I've sent the request to {state.hotel.hotel_name}."
                    )
                    event = await self._await_event(reply_timeout_seconds)
                    if event.kind == "timeout":
                        state, give_up = d.on_timeout(state, followup_max)
                        if give_up:
                            return state, (trigger_kind, trigger_body, trigger_subject), False
                        trigger_kind, trigger_body = "timeout_followup", ""
                    elif event.kind == "delivery":
                        state = d.mark_cant_progress(state, f"delivery failed: {event.description}")
                        return state, (trigger_kind, trigger_body, trigger_subject), False
                    elif event.kind == "reply":
                        await workflow.execute_activity(
                            ConciergeActivities.record_inbound_reply,
                            args=[
                                state.booking_id,
                                event.from_email or "",
                                event.subject,
                                event.body,
                                "hotel",
                            ],
                            start_to_close_timeout=ACTIVITY_TIMEOUT,
                            retry_policy=SIDE_EFFECT_RETRY_POLICY,
                        )
                        await self._notify_progress(
                            state, "hotel_replied", "The hotel got back to us — I'll update you shortly."
                        )
                        trigger_kind, trigger_body, trigger_subject = "hotel_reply", event.body, event.subject
                    elif event.kind == "followup":
                        state = d.add_client_followup_topics(state, _topics_from_text(event.body))
                        trigger_kind, trigger_body = "compose_initial", ""
                case "resolved":
                    state = d.apply_resolutions(state, intent.resolutions)
                    trigger_kind, trigger_body = "compose_initial", ""
                case "need_more_info":
                    await workflow.execute_activity(
                        ConciergeActivities.relay_to_client,
                        args=[state.booking_id, NEED_INFO_SUBJECT, intent.question_to_client or intent.reason or ""],
                        start_to_close_timeout=ACTIVITY_TIMEOUT,
                        retry_policy=SIDE_EFFECT_RETRY_POLICY,
                    )
                    body = await self._await_followup(reply_timeout_seconds=clarify_timeout_seconds)
                    if body is None:
                        return state, (trigger_kind, trigger_body, trigger_subject), False
                    state = d.add_client_followup_topics(state, _topics_from_text(body))
                    trigger_kind, trigger_body = "compose_initial", ""
            await self._persist(state)
        return state, (trigger_kind, trigger_body, trigger_subject), False

    async def _finalize(self, state: BookingState) -> None:  # pragma: no cover - exercised by gated Temporal E2E
        report = await workflow.execute_activity(
            ConciergeActivities.build_report,
            args=[state],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
            retry_policy=SIDE_EFFECT_RETRY_POLICY,
        )
        await workflow.execute_activity(
            ConciergeActivities.relay_to_client,
            args=[state.booking_id, REPORT_SUBJECT, report],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
            retry_policy=SIDE_EFFECT_RETRY_POLICY,
        )
        state.lifecycle = "report_sent"
        await self._persist(state)

    async def _await_reactivation(self, state: BookingState, reactivation_timeout_seconds: int) -> BookingState | None:  # pragma: no cover - exercised by gated Temporal E2E
        body = await self._await_followup(reply_timeout_seconds=reactivation_timeout_seconds)
        if body is None:
            return None
        state = d.add_client_followup_topics(state, _topics_from_text(body))
        state.lifecycle = "in_conversation"
        return state

    async def _continue_as_new(  # pragma: no cover - exercised by gated Temporal E2E
        self,
        state: BookingState,
        trigger_kind: str,
        trigger_body: str,
        trigger_subject: str | None,
        *,
        reply_timeout_seconds: int,
        followup_max: int,
        clarify_timeout_seconds: int,
        reactivation_timeout_seconds: int,
        continue_as_new_threshold: int,
    ) -> None:
        """Hand off to a fresh run with a clean Event History, preserving state + in-flight signals."""
        resume = ResumeInput(
            state=state,
            trigger_kind=trigger_kind,
            trigger_body=trigger_body,
            trigger_subject=trigger_subject,
            pending_replies=list(self._hotel_replies),
            pending_followups=list(self._client_followups),
            pending_delivery_failures=list(self._delivery_failures),
        )
        await workflow.continue_as_new(
            args=[
                RunInput(resume=resume),
                reply_timeout_seconds,
                followup_max,
                clarify_timeout_seconds,
                reactivation_timeout_seconds,
                continue_as_new_threshold,
            ]
        )

    # --- primitives ---

    async def _agent_turn(  # pragma: no cover - exercised by gated Temporal E2E
        self, state: BookingState, kind: str, body: str, subject: str | None
    ) -> IntentResult:
        return await workflow.execute_activity(
            ConciergeActivities.agent_turn,
            args=[state.booking_id, state, kind, body, subject],
            start_to_close_timeout=LLM_ACTIVITY_TIMEOUT,
            retry_policy=LLM_RETRY_POLICY,
        )

    async def _send_email(self, state: BookingState, intent: IntentResult) -> None:  # pragma: no cover - exercised by gated Temporal E2E
        to = intent.to or (state.hotel.email or "")
        if not to:
            return
        await workflow.execute_activity(
            ConciergeActivities.send_email,
            args=[state.booking_id, to, intent.subject or "Hotel request", intent.body or "", intent.step or "initial"],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
            retry_policy=SIDE_EFFECT_RETRY_POLICY,
        )

    async def _persist(self, state: BookingState) -> None:  # pragma: no cover - exercised by gated Temporal E2E
        await workflow.execute_activity(
            ConciergeActivities.update_booking_state,
            args=[state],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
            retry_policy=SIDE_EFFECT_RETRY_POLICY,
        )

    async def _notify_progress(self, state: BookingState, kind: str, body: str) -> None:  # pragma: no cover - exercised by gated Temporal E2E
        """Push a user-visible progress event (design D7). Gated behind the progress-push patch."""
        if not workflow.patched(PROGRESS_PUSH_PATCH):
            return
        await workflow.execute_activity(
            ConciergeActivities.notify_progress,
            args=[state.booking_id, kind, PROGRESS_SUBJECTS.get(kind, kind), body],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
            retry_policy=SIDE_EFFECT_RETRY_POLICY,
        )

    async def _await_event(self, reply_timeout_seconds: int) -> PendingEvent:  # pragma: no cover - exercised by gated Temporal E2E
        try:
            await workflow.wait_condition(self._has_event, timeout=reply_timeout_seconds)
        except TimeoutError:
            return PendingEvent(kind="timeout")
        if self._delivery_failures:
            severity, description = self._delivery_failures.popleft()
            return PendingEvent(kind="delivery", severity=severity, description=description)
        if self._hotel_replies:
            from_email, body, subject = self._hotel_replies.popleft()
            return PendingEvent(kind="reply", from_email=from_email, body=body, subject=subject)
        if self._client_followups:
            return PendingEvent(kind="followup", body=self._client_followups.popleft())
        return PendingEvent(kind="timeout")  # pragma: no cover - defensive

    async def _await_followup(self, reply_timeout_seconds: int) -> str | None:  # pragma: no cover - exercised by gated Temporal E2E
        try:
            await workflow.wait_condition(lambda: bool(self._client_followups), timeout=reply_timeout_seconds)
        except TimeoutError:
            return None
        return self._client_followups.popleft()


def _topics_from_text(body: str) -> list[str]:
    """Best-effort extraction of distinct topic labels from a free-text follow-up.

    v1: treat each non-empty line as a potential topic; the agent incorporates them as context.
    """
    return [line.strip().lower() for line in body.splitlines() if line.strip()]
