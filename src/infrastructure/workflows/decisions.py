"""Pure workflow-transition logic (spec 6.5 / design lifecycle).

These reducers are deterministic and free of I/O, so the workflow's decision logic is unit-tested
without a Temporal server. The workflow class wires signals/timers/activities around them.
"""

from __future__ import annotations

from copy import deepcopy

from infrastructure.workflows.dtos import (
    BookingState,
    ContactResult,
    ExtractedData,
    ResolutionData,
    TopicData,
)

DEFAULT_TOPIC_LABELS = ("early-checkin", "room-upgrade")


def state_from_extraction(
    booking_id: str, client_token: str, extracted: ExtractedData, language: str = "en"
) -> BookingState:
    """Build the initial booking state from extraction results.

    Default topics (early-checkin, room-upgrade) plus any wish-derived topics are created OPEN.
    """
    needs_discovery = extracted.hotel_email is None
    topics = [TopicData(topic_id=topic_id_for(booking_id, label), label=label) for label in DEFAULT_TOPIC_LABELS]
    topics += [
        TopicData(topic_id=topic_id_for(booking_id, label), label=label) for label in extracted.wish_topics
    ]
    return BookingState(
        booking_id=booking_id,
        client_token=client_token,
        hotel=_hotel_from_extraction(extracted),
        booking_ref=extracted.booking_ref,
        check_in=extracted.check_in,
        check_out=extracted.check_out,
        guests=list(extracted.guests),
        room_type=extracted.room_type,
        language=language or "en",
        wishes=list(extracted.wishes),
        topics=topics,
        lifecycle="extracted",
        needs_discovery=needs_discovery,
    )


def _hotel_from_extraction(extracted: ExtractedData):
    from infrastructure.workflows.dtos import HotelContactData

    return HotelContactData(
        hotel_name=extracted.hotel_name,
        email=extracted.hotel_email,
        website=extracted.hotel_website,
        discovered=False,
    )


def topic_id_for(booking_id: str, label: str) -> str:
    return f"{booking_id}:t:{label.lower().replace(' ', '-')}"


def apply_contact(state: BookingState, contact: ContactResult) -> BookingState:
    """Apply discovery results. If no contact found, the booking cannot progress."""
    new = deepcopy(state)
    if not contact.found or not contact.email:
        new.lifecycle = "cant_progress"
        new.needs_discovery = False
        return new
    new.hotel.email = contact.email
    new.hotel.website = contact.website or new.hotel.website
    new.hotel.discovered = True
    if contact.language:
        new.language = contact.language
    new.needs_discovery = False
    new.lifecycle = "contact_ready"
    return new


def record_email_sent(state: BookingState, step: str | None) -> BookingState:
    """After sending an email to the hotel, we await its reply."""
    new = deepcopy(state)
    new.lifecycle = "awaiting_reply"
    return new


def apply_resolutions(state: BookingState, resolutions: list[ResolutionData]) -> BookingState:
    """Apply the agent's topic resolutions from a parsed hotel reply."""
    new = deepcopy(state)
    by_id = {t.topic_id: t for t in new.topics}
    for res in resolutions:
        topic = by_id.get(res.topic_id)
        if topic is None:
            continue
        topic.status = res.status
        topic.result = res.result or topic.result
    new.lifecycle = "topics_resolved" if new.all_topics_terminal() else "in_conversation"
    return new


def on_timeout(state: BookingState, max_attempts: int) -> tuple[BookingState, bool]:
    """Handle a reply timeout.

    Returns (new_state, give_up). When attempts are exhausted, open topics become unresolved.
    """
    new = deepcopy(state)
    new.followup_attempts += 1
    give_up = new.followup_attempts > max_attempts
    if give_up:
        for t in new.topics:
            if t.status == "open":
                t.status = "unresolved"
                t.result = t.result or "no reply from hotel"
        new.lifecycle = "topics_resolved" if new.all_topics_terminal() else "in_conversation"
    return new, give_up


def should_build_report(state: BookingState) -> bool:
    """All topics are terminal (resolved/unresolved/cant_progress)."""
    return state.all_topics_terminal()


def add_client_followup_topics(state: BookingState, new_labels: list[str]) -> BookingState:
    """A client follow-up may reopen or add topics, returning the booking to conversation."""
    new = deepcopy(state)
    existing = {t.label.lower() for t in new.topics}
    for label in new_labels:
        if label.lower() not in existing:
            new.topics.append(TopicData(topic_id=topic_id_for(new.booking_id, label), label=label))
            existing.add(label.lower())
    new.lifecycle = "in_conversation"
    return new


def mark_cant_progress(state: BookingState, reason: str) -> BookingState:
    new = deepcopy(state)
    new.lifecycle = "cant_progress"
    for t in new.topics:
        if t.status == "open":
            t.status = "cant_progress"
            t.result = reason
    return new
