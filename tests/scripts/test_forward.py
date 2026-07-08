from datetime import UTC, datetime
from email import message_from_bytes

from scripts.forward import _forward_subject, pick_wish, wrap_as_forward
from scripts.types import Candidate, ClassifiedCandidate


def _item(subject: str = "Booking Confirmation", body: str = "Hotel Grand, 2 nights") -> ClassifiedCandidate:
    return ClassifiedCandidate(
        candidate=Candidate(
            sender="reservations@marriott.com",
            subject=subject,
            date=datetime(2026, 2, 1, 9, 0, tzinfo=UTC),
            body=body,
        ),
        is_hotel_confirmation=True,
        system="marriott.com",
        confidence=0.9,
        skip_reason=None,
    )


class TestWrapAsForward:
    def test_headers_and_subject_prefix(self) -> None:
        msg = wrap_as_forward(_item(), client_email="me@x.com", recipient="c.tok@kkr-hotel.com", wish_cover=None)
        assert msg["From"] == "me@x.com"
        assert msg["To"] == "c.tok@kkr-hotel.com"
        assert msg["Subject"] == "Fwd: Booking Confirmation"

    def test_without_cover_starts_at_original_block(self) -> None:
        msg = wrap_as_forward(_item(), client_email="me@x.com", recipient="c.t@k.com", wish_cover=None)
        body = msg.get_content()
        assert body.startswith("-----Original Message-----")
        assert "reservations@marriott.com" in body
        assert "Hotel Grand, 2 nights" in body

    def test_with_cover_puts_wish_then_separator(self) -> None:
        msg = wrap_as_forward(
            _item(), client_email="me@x.com", recipient="c.t@k.com", wish_cover="High floor please."
        )
        body = msg.get_content()
        wish_idx = body.index("High floor please.")
        sep_idx = body.index("-----Original Message-----")
        assert wish_idx < sep_idx

    def test_serializes_to_valid_eml(self) -> None:
        msg = wrap_as_forward(_item(), client_email="me@x.com", recipient="c.t@k.com", wish_cover="x")
        parsed = message_from_bytes(bytes(msg))
        assert parsed["From"] == "me@x.com"
        assert parsed["Subject"] == "Fwd: Booking Confirmation"
        assert "-----Original Message-----" in str(parsed.get_payload())

    def test_subject_already_fwd_is_not_double_prefixed(self) -> None:
        assert _forward_subject("Fwd: Booking") == "Fwd: Booking"
        assert _forward_subject("booking") == "Fwd: booking"
        assert _forward_subject("") == "Fwd: (no subject)"


class TestPickWish:
    def test_none_mode_returns_none(self) -> None:
        assert pick_wish(0, mode="none") is None

    def test_mixed_mode_is_deterministic_and_includes_none(self) -> None:
        first = pick_wish(0, mode="mixed")
        assert pick_wish(0, mode="mixed") == first  # deterministic
        # pool contains an empty entry → some index yields None
        covers = {pick_wish(i, mode="mixed") is None for i in range(len(("a", "b", "")))}
        assert True in covers
