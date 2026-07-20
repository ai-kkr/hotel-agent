"""Integration tests for the FlightAPI client (cache + TTL policy), on ``respx``-mocked HTTP.

Drives :meth:`FlightClient.track` end-to-end through cache -> http -> pydantic, exercising the
two-tier TTL policy (config force-override vs. proximity-based tiers) per
``openspec/changes/add-flight-tracking/design.md`` (D4/D5).
"""

from datetime import UTC, datetime, timedelta

import httpx
import respx
from src.config import Settings
from src.integrations.flights.cache import FlightCache
from src.integrations.flights.client import FlightClient


def _payload(departure_iso: str, arrival_iso: str) -> list[dict]:
    """A FlightAPI-shaped response array (see docs sample in design.md)."""
    return [
        {
            "departure": {
                "airport": "Barcelona",
                "airportCity": "Barcelona",
                "airportCode": "BCN",
                "terminal": "1",
                "gate": None,
                "scheduledTime": "14:55, Jul 16",
                "estimatedTime": None,
                "departureDateTime": departure_iso,
            }
        },
        {
            "arrival": {
                "airport": "Heathrow",
                "airportCity": "London",
                "airportCode": "LHR",
                "terminal": "5",
                "gate": None,
                "scheduledTime": "16:15, Jul 16",
                "arrivalDateTime": arrival_iso,
            }
        },
    ]


def _client(tmp_path, **settings_overrides) -> FlightClient:
    settings = Settings(
        flightapi_key="testkey",
        flight_cache_dir=str(tmp_path),
        **settings_overrides,
    )
    return FlightClient(
        api_key=settings.flightapi_key,
        cache=FlightCache(settings.flight_cache_dir),
        settings=settings,
    )


@respx.mock
async def test_force_ttl_serves_second_lookup_from_cache(tmp_path):
    """7.1: with a force-TTL override set, a repeat lookup for the same flight hits the cache."""
    departure = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    route = respx.get("https://api.flightapi.io/airline/testkey").mock(
        return_value=httpx.Response(200, json=_payload(departure, departure))
    )
    client = _client(tmp_path, flight_cache_force_ttl_seconds=3600)

    first = await client.track("100", "AA", "20260901")
    second = await client.track("100", "AA", "20260901")

    assert route.call_count == 1  # second call served from cache, no second HTTP hit
    assert first.departure is not None
    assert first.departure.airport_code == "BCN"
    assert second.departure is not None
    assert second.departure.airport_code == "BCN"
    assert second.arrival is not None
    assert second.arrival.airport_code == "LHR"


@respx.mock
async def test_proximity_ttl_day_of_bypasses_far_out_caches(tmp_path):
    """7.2: day-of departure bypasses the cache (two HTTP hits); a far-out flight caches (one hit)."""
    client = _client(tmp_path)  # force_ttl unset -> proximity policy governs

    # Day-of: departure is 2 hours away (< near_boundary_days=1) -> TTL 0, always a fresh HTTP call.
    soon = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    day_of_route = respx.get(
        "https://api.flightapi.io/airline/testkey", params={"num": "200"}
    ).mock(return_value=httpx.Response(200, json=_payload(soon, soon)))

    await client.track("200", "BB", "20260716")
    await client.track("200", "BB", "20260716")
    assert day_of_route.call_count == 2

    # Far-out: departure is 30 days away (> far_boundary_days=7) -> cached with the long TTL.
    far = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    far_route = respx.get("https://api.flightapi.io/airline/testkey", params={"num": "300"}).mock(
        return_value=httpx.Response(200, json=_payload(far, far))
    )

    await client.track("300", "CC", "20260901")
    await client.track("300", "CC", "20260901")
    assert far_route.call_count == 1
