from datetime import UTC, datetime

from scripts.classifier import BatchClassification, CandidateClassification, ConfirmationClassifier
from scripts.types import Candidate

from tests.agents.fakes import FakeChatModel


def _candidate(subject: str, sender: str = "reservations@example.com", body: str = "body") -> Candidate:
    return Candidate(sender=sender, subject=subject, date=datetime(2026, 1, 1, tzinfo=UTC), body=body)


class TestConfirmationClassifier:
    async def test_keeps_confirmed_and_skips_below_threshold_or_irrelevant(self) -> None:
        candidates = [
            _candidate("Your booking confirmation", "stay@marriott.com"),
            _candidate("Your booking", "noreply@booking.com"),
            _candidate("50% off flights!", "deals@expedia.com"),
        ]
        batch = BatchClassification(
            items=[
                CandidateClassification(index=0, is_hotel_confirmation=True, system="marriott.com", confidence=0.9),
                CandidateClassification(index=1, is_hotel_confirmation=True, system="booking.com", confidence=0.4),
                CandidateClassification(
                    index=2, is_hotel_confirmation=False, system="expedia.com", confidence=0.2, skip_reason="marketing"
                ),
            ]
        )
        model = FakeChatModel().with_structured(batch)
        classifier = ConfirmationClassifier(model, confidence_threshold=0.6)

        result = await classifier.classify(candidates)

        assert [r.is_hotel_confirmation for r in result] == [True, False, False]
        assert result[0].system == "marriott.com"
        assert result[1].skip_reason is not None  # below threshold
        assert result[2].skip_reason == "marketing"

    async def test_empty_candidates_returns_empty(self) -> None:
        classifier = ConfirmationClassifier(FakeChatModel(), confidence_threshold=0.6)
        assert await classifier.classify([]) == []

    async def test_falls_back_to_sender_domain_when_system_missing(self) -> None:
        candidate = _candidate("Confirmation", "stay@hilton.com")
        batch = BatchClassification(
            items=[CandidateClassification(index=0, is_hotel_confirmation=True, system=None, confidence=0.95)]
        )
        model = FakeChatModel().with_structured(batch)
        classifier = ConfirmationClassifier(model, confidence_threshold=0.6)

        result = await classifier.classify([candidate])

        assert result[0].system == "hilton.com"
