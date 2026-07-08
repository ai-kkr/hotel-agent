from __future__ import annotations

import pytest

from domain.ids import (
    AddressRoute,
    EmailAddress,
    LocalPart,
    conversation_address,
    intake_address,
    route,
)


class TestEmailAddress:
    def test_lowercases_and_strips(self) -> None:
        assert EmailAddress("  Hotel@Example.COM  ").value == "hotel@example.com"

    @pytest.mark.parametrize("bad", ["not-an-email", "a@b", "@x.com", "x@.com", "x @y.com"])
    def test_rejects_invalid(self, bad: str) -> None:
        with pytest.raises(ValueError):
            EmailAddress(bad)

    def test_str(self) -> None:
        assert str(EmailAddress("a@b.com")) == "a@b.com"


class TestLocalPart:
    @pytest.mark.parametrize("bad", ["", "  ", "has space", "ws@", "é.accent"])
    def test_rejects_invalid(self, bad: str) -> None:
        with pytest.raises(ValueError):
            LocalPart(bad)

    def test_accepts_valid(self) -> None:
        assert LocalPart("c.abc-123_X").value == "c.abc-123_x"


class TestRoute:
    def test_intake(self) -> None:
        r = route("c.abc123")
        assert r == AddressRoute(kind="intake", token="abc123")
        assert r.is_intake and not r.is_conversation

    def test_conversation(self) -> None:
        r = route("B.42")  # case-insensitive
        assert r.booking_id == "42"
        assert r.is_conversation

    def test_unknown_for_bare_prefix(self) -> None:
        assert route("c.").kind == "unknown"
        assert route("b.").kind == "unknown"

    def test_unknown_for_garbage(self) -> None:
        assert route("random").kind == "unknown"
        assert route("x.123").kind == "unknown"


class TestAddressBuilders:
    def test_intake_address(self) -> None:
        a = intake_address("abc", "kkr-hotel.com")
        assert a.value == "c.abc@kkr-hotel.com"

    def test_conversation_address(self) -> None:
        a = conversation_address("42", "kkr-hotel.com")
        assert a.value == "b.42@kkr-hotel.com"

    def test_intake_address_rejects_empty_token(self) -> None:
        with pytest.raises(ValueError):
            intake_address("", "kkr-hotel.com")
