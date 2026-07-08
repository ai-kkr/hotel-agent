from __future__ import annotations

from datetime import date

import pytest

from domain.enums import TopicStatus
from domain.extraction import ExtractedBooking
from domain.ids import EmailAddress
from domain.intents import (
    ComposeInitial,
    ParseHotelReply,
    Resolved,
    SearchDone,
    SendEmail,
    TimeoutFollowup,
    TopicResolution,
)


class TestSendEmail:
    def _make(self, **over: object) -> SendEmail:
        base = dict(
            to=EmailAddress("h@x.com"),
            subject="Hello",
            body="Body",
            language="en",
            topic_ids=["b:t:x"],
            step="initial",
        )
        base.update(over)
        return SendEmail(**base)  # type: ignore[arg-type]

    def test_valid(self) -> None:
        i = self._make()
        assert i.step == "initial"

    @pytest.mark.parametrize("field,val", [("subject", "  "), ("body", ""), ("step", "")])
    def test_rejects_empty(self, field: str, val: str) -> None:
        with pytest.raises(ValueError):
            self._make(**{field: val})


class TestTopicResolution:
    def test_resolved_requires_result(self) -> None:
        with pytest.raises(ValueError):
            TopicResolution(topic_id="b:t:x", status=TopicStatus.RESOLVED, result=" ")

    def test_open_resolution_ok(self) -> None:
        r = TopicResolution(topic_id="b:t:x", status=TopicStatus.OPEN, result="pending")
        assert r.status is TopicStatus.OPEN


class TestSearchDone:
    def test_defaults_to_english(self) -> None:
        s = SearchDone(hotel_name="X")
        assert s.language == "en" and s.found is True

    def test_requires_hotel_name(self) -> None:
        with pytest.raises(ValueError):
            SearchDone(hotel_name=" ")


class TestExtractedBooking:
    def _make(self, **over: object) -> ExtractedBooking:
        base = dict(
            hotel_name="Grand",
            confidence=0.9,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 3),
            booking_ref="R1",
        )
        base.update(over)
        return ExtractedBooking(**base)  # type: ignore[arg-type]

    def test_confident_when_no_missing_required(self) -> None:
        assert self._make().is_confident is True

    def test_not_confident_when_missing(self) -> None:
        assert self._make(missing_required=["booking_ref"]).is_confident is False

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValueError):
            self._make(confidence=1.5)
        with pytest.raises(ValueError):
            self._make(confidence=-0.1)

    def test_language_hint_from_tld(self) -> None:
        eb = self._make(hotel_website="https://grand.fr")
        assert eb.hotel_language_hint() == "fr"

    def test_language_hint_none_without_website(self) -> None:
        assert self._make().hotel_language_hint() is None


class TestTriggers:
    def test_distinct_triggers(self) -> None:
        assert isinstance(ComposeInitial(), ComposeInitial)
        assert isinstance(ParseHotelReply(body="x"), ParseHotelReply)
        assert isinstance(TimeoutFollowup(), TimeoutFollowup)


class TestResolved:
    def test_default_empty(self) -> None:
        assert Resolved().resolutions == []
