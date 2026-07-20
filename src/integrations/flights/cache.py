"""On-disk async cache for FlightAPI responses (cashews DiskCache backend) + TTL policy.

The cache stores the **raw API JSON payload** (list of ``{"departure": …}``/``{"arrival": …}``
objects), keyed by the request parameters; pydantic validation happens on read, in
:mod:`.client`, not here — so a model change never invalidates the cache (design D3), and a
corrupted/unparseable cached entry is simply treated as a miss by the caller.

TTL is resolved dynamically (:func:`resolve_ttl`) from data (``departureDateTime``) that is only
known *after* the network call, so caching is done with manual ``get``/``set`` rather than a
declarative ``@cache(ttl=...)`` decorator (design D5).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from cashews import Cache

__all__ = ["FlightCache", "resolve_ttl"]


class FlightCache:
    """Thin wrapper over a cashews DiskCache backend, storing raw FlightAPI JSON payloads."""

    def __init__(self, directory: str) -> None:
        self._cache = Cache()
        self._cache.setup(f"disk://?directory={directory}&timeout=1")

    @staticmethod
    def key_for(num: str, name: str, date: str, depap: str | None) -> str:
        """``sha1(num|name|date|depap)`` — one cache entry per distinct set of request params."""
        raw = f"{num}|{name}|{date}|{depap or ''}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    async def get_json(self, key: str) -> list | dict | None:
        """Return the cached raw payload for ``key``, or ``None`` on a miss."""
        return await self._cache.get(key, default=None)

    async def set_json(self, key: str, payload: list | dict, ttl: int) -> None:
        """Cache ``payload`` under ``key`` for ``ttl`` seconds. A no-op when ``ttl <= 0``."""
        if ttl <= 0:
            return
        await self._cache.set(key, payload, expire=ttl)


def resolve_ttl(
    departure_dt: datetime | None,
    now: datetime,
    *,
    force_ttl: int | None,
    far_seconds: int,
    near_seconds: int,
    far_boundary_days: int,
    near_boundary_days: int,
) -> int:
    """Resolve the cache TTL (seconds) for a flight departing at ``departure_dt``.

    Precedence (design D4):

    1. ``force_ttl`` if set — pins a fixed TTL unconditionally, before any data dependency (dev
       stand / tests, to cap FlightAPI spend; ``0`` means "always bypass").
    2. Otherwise a proximity-based tier keyed off ``departure_dt - now``:
       - unknown departure time → treated as far-out (long TTL) — sparse/no data yet shouldn't
         hammer the API on every scheduled check;
       - more than ``far_boundary_days`` away → ``far_seconds``;
       - between ``near_boundary_days`` and ``far_boundary_days`` → ``near_seconds``;
       - within ``near_boundary_days`` (day of flight) → ``0`` (bypass — re-asked gate/delay/ETA
         questions always hit the network).
    """
    if force_ttl is not None:
        return force_ttl

    if departure_dt is None:
        return far_seconds

    if departure_dt.tzinfo is None:
        departure_dt = departure_dt.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    days_out = (departure_dt - now).total_seconds() / 86400
    if days_out > far_boundary_days:
        return far_seconds
    if days_out >= near_boundary_days:
        return near_seconds
    return 0
