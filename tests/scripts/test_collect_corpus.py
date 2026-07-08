import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.classifier import BatchClassification, CandidateClassification
from scripts.collect_corpus import collect
from scripts.types import Candidate

from tests.agents.fakes import FakeChatModel


class _FakeSource:
    def __init__(self, candidates: list[Candidate]) -> None:
        self._candidates = candidates

    def search(self, query: str, *, limit: int) -> list[Candidate]:
        return self._candidates[:limit]


def _candidate(subject: str, sender: str, body: str = "confirmation details") -> Candidate:
    return Candidate(sender=sender, subject=subject, date=datetime(2026, 1, 1, tzinfo=UTC), body=body)


class TestCollectEndToEnd:
    def test_full_pipeline_no_network(self, tmp_path: Path) -> None:
        candidates = [
            _candidate("Booking", "a@marriott.com"),
            _candidate("Booking", "b@booking.com"),
            _candidate("Booking", "c@hilton.com"),
            _candidate("Flights sale", "d@expedia.com"),  # irrelevant → skipped
            _candidate("Booking", "e@marriott.com"),  # duplicate system
        ]
        batch = BatchClassification(
            items=[
                CandidateClassification(index=0, is_hotel_confirmation=True, system="marriott.com", confidence=0.95),
                CandidateClassification(index=1, is_hotel_confirmation=True, system="booking.com", confidence=0.95),
                CandidateClassification(index=2, is_hotel_confirmation=True, system="hilton.com", confidence=0.95),
                CandidateClassification(
                    index=3, is_hotel_confirmation=False, system="expedia.com", confidence=0.2, skip_reason="marketing"
                ),
                CandidateClassification(index=4, is_hotel_confirmation=True, system="marriott.com", confidence=0.95),
            ]
        )
        model = FakeChatModel().with_structured(batch)

        summary = collect(
            source=_FakeSource(candidates),
            model=model,
            query="subject:booking",
            count=3,
            client_email="owner@example.com",
            recipient="c.demo@kkr-hotel.com",
            out_dir=tmp_path,
            wishes_mode="none",
        )

        assert summary.candidates_found == 5
        assert summary.confirmed == 4
        assert summary.skipped == 1
        assert summary.selected == 3
        assert summary.unique_systems == 3
        assert len(summary.written_files) == 3

        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        systems = [e["system"] for e in manifest]
        assert systems == ["marriott.com", "booking.com", "hilton.com"]  # one per distinct system

        for entry in manifest:
            assert entry["filename"].endswith(".eml")
            assert (tmp_path / entry["filename"]).exists()

    def test_empty_source_writes_nothing(self, tmp_path: Path) -> None:
        summary = collect(
            source=_FakeSource([]),
            model=FakeChatModel(),
            query="subject:booking",
            count=3,
            client_email="owner@example.com",
            recipient="c.demo@kkr-hotel.com",
            out_dir=tmp_path,
        )
        assert summary.candidates_found == 0
        assert summary.selected == 0
        assert (tmp_path / "manifest.json").exists()  # manifest still written (empty list)
