from __future__ import annotations

from infrastructure.workflows.decisions import (
    add_client_followup_topics,
    apply_contact,
    apply_resolutions,
    mark_cant_progress,
    on_timeout,
    should_build_report,
    state_from_extraction,
    topic_id_for,
)
from infrastructure.workflows.dtos import (
    ContactResult,
    ExtractedData,
    ResolutionData,
)


def _extracted(**over: object) -> ExtractedData:
    base = dict(
        hotel_name="Grand",
        hotel_email="stay@grand.com",
        booking_ref="R1",
        check_in="2026-02-01",
        check_out="2026-02-04",
        confidence=0.9,
    )
    base.update(over)
    return ExtractedData(**base)  # type: ignore[arg-type]


class TestStateFromExtraction:
    def test_creates_default_topics(self) -> None:
        state = state_from_extraction("b1", "tok", _extracted())
        assert {t.label for t in state.topics} == {"early-checkin", "room-upgrade"}
        assert all(t.status == "open" for t in state.topics)
        assert state.lifecycle == "extracted"
        assert state.needs_discovery is False

    def test_needs_discovery_without_hotel_email(self) -> None:
        state = state_from_extraction("b1", "tok", _extracted(hotel_email=None))
        assert state.needs_discovery is True

    def test_wish_topics_become_topics(self) -> None:
        state = state_from_extraction("b1", "tok", _extracted(wish_topics=["late-checkout"]))
        assert "late-checkout" in {t.label for t in state.topics}

    def test_topic_id_for(self) -> None:
        assert topic_id_for("b1", "Late Checkout") == "b1:t:late-checkout"


class TestApplyContact:
    def test_found_sets_contact_ready(self) -> None:
        state = state_from_extraction("b1", "tok", _extracted(hotel_email=None))
        out = apply_contact(state, ContactResult(email="r@grand.fr", language="fr", found=True))
        assert out.lifecycle == "contact_ready"
        assert out.hotel.email == "r@grand.fr"
        assert out.language == "fr"
        assert out.needs_discovery is False

    def test_not_found_cant_progress(self) -> None:
        state = state_from_extraction("b1", "tok", _extracted(hotel_email=None))
        out = apply_contact(state, ContactResult(found=False))
        assert out.lifecycle == "cant_progress"


class TestApplyResolutions:
    def test_partial_resolution_keeps_open(self) -> None:
        state = state_from_extraction("b1", "tok", _extracted())
        out = apply_resolutions(
            state,
            [ResolutionData(topic_id=topic_id_for("b1", "early-checkin"), status="resolved", result="granted")],
        )
        assert out.lifecycle == "in_conversation"
        assert out.topics[0].status == "resolved"
        assert out.topics[1].status == "open"

    def test_all_resolved(self) -> None:
        state = state_from_extraction("b1", "tok", _extracted())
        out = apply_resolutions(
            state,
            [
                ResolutionData(topic_id=topic_id_for("b1", "early-checkin"), status="resolved", result="ok"),
                ResolutionData(topic_id=topic_id_for("b1", "room-upgrade"), status="resolved", result="ok"),
            ],
        )
        assert out.lifecycle == "topics_resolved"
        assert should_build_report(out) is True


class TestOnTimeout:
    def test_increments_and_continues(self) -> None:
        state = state_from_extraction("b1", "tok", _extracted())
        out, give_up = on_timeout(state, max_attempts=2)
        assert out.followup_attempts == 1
        assert give_up is False

    def test_give_up_marks_unresolved(self) -> None:
        state = state_from_extraction("b1", "tok", _extracted())
        state.followup_attempts = 2
        out, give_up = on_timeout(state, max_attempts=2)
        assert give_up is True
        assert all(t.status == "unresolved" for t in out.topics)


class TestFollowupAndCantProgress:
    def test_add_followup_topics(self) -> None:
        state = state_from_extraction("b1", "tok", _extracted())
        out = add_client_followup_topics(state, ["late-checkout"])
        assert "late-checkout" in {t.label for t in out.topics}
        assert out.lifecycle == "in_conversation"

    def test_mark_cant_progress(self) -> None:
        state = state_from_extraction("b1", "tok", _extracted())
        out = mark_cant_progress(state, "bounce")
        assert out.lifecycle == "cant_progress"
        assert all(t.status == "cant_progress" for t in out.topics)
