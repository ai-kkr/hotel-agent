from datetime import UTC, datetime

from scripts.selector import select_diverse
from scripts.types import Candidate, ClassifiedCandidate


def _classified(system: str, confirmed: bool = True) -> ClassifiedCandidate:
    return ClassifiedCandidate(
        candidate=Candidate(
            sender=f"x@{system}", subject="s", date=datetime(2026, 1, 1, tzinfo=UTC), body="b"
        ),
        is_hotel_confirmation=confirmed,
        system=system,
        confidence=0.9,
        skip_reason=None if confirmed else "nope",
    )


class TestSelectDiverse:
    def test_more_systems_than_count_picks_one_each(self) -> None:
        items = [_classified(f"sys{ i }") for i in range(4)]
        chosen = select_diverse(items, count=2)
        assert [c.system for c in chosen] == ["sys0", "sys1"]

    def test_fewer_systems_than_count_backfills(self) -> None:
        items = [
            _classified("booking.com"),
            _classified("booking.com"),
            _classified("marriott.com"),
            _classified("booking.com"),
        ]
        chosen = select_diverse(items, count=3)
        assert len(chosen) == 3
        assert {c.system for c in chosen} == {"booking.com", "marriott.com"}
        # two distinct systems first, then one backfill from booking.com
        assert chosen[0].system == "booking.com"
        assert chosen[1].system == "marriott.com"

    def test_empty_pool_returns_empty(self) -> None:
        assert select_diverse([], count=5) == []

    def test_all_unconfirmed_returns_empty(self) -> None:
        items = [_classified("booking.com", confirmed=False)]
        assert select_diverse(items, count=3) == []

    def test_zero_count_returns_empty(self) -> None:
        items = [_classified("booking.com")]
        assert select_diverse(items, count=0) == []
