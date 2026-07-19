"""Tests for the per-message current-time context stamp (bot entry point)."""

from datetime import UTC, datetime

from src.bot.core import build_now_context


def test_utc_only_when_zones_unset():
    out = build_now_context(datetime(2026, 7, 19, 12, 30, tzinfo=UTC), None, None)
    assert "UTC 2026-07-19 12:30" in out
    assert "дом" not in out
    assert "поездка" not in out
    assert out.startswith("[текущее время клиента —")


def test_includes_both_zones_when_set():
    out = build_now_context(
        datetime(2026, 7, 19, 12, 30, tzinfo=UTC),
        "Europe/Moscow",
        "Asia/Shanghai",
    )
    # Same UTC instant rendered in each zone.
    assert "UTC 2026-07-19 12:30" in out
    assert "дом (Europe/Moscow) 2026-07-19 15:30" in out
    assert "поездка (Asia/Shanghai) 2026-07-19 20:30" in out


def test_invalid_zone_is_skipped_not_raised():
    out = build_now_context(datetime(2026, 7, 19, 12, 30, tzinfo=UTC), "Not/A/Zone", None)
    # Bad zone dropped silently; UTC still present.
    assert "UTC 2026-07-19 12:30" in out
    assert "дом" not in out
