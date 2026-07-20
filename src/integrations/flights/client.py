"""Async client for the FlightAPI flight-status tracking endpoint.

``GET https://api.flightapi.io/airline/{api_key}?num=&name=&date=[&depap=]`` returns a two-item
array of single-key objects (``{"departure": {...}}`` / ``{"arrival": {...}}``); this client
flattens that into one :class:`~.models.FlightStatus`, fronted by an on-disk cache
(:class:`~.cache.FlightCache`) whose TTL is resolved dynamically (:func:`~.cache.resolve_ttl`)
from the parsed ``departureDateTime`` (design D1/D5 in
``openspec/changes/add-flight-tracking/design.md``).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from src.config import Settings
from src.logging import get_logger

from .cache import FlightCache, resolve_ttl
from .models import ArrivalInfo, DepartureInfo, FlightStatus

__all__ = ["FlightClient"]

log = get_logger(__name__)

_BASE_URL = "https://api.flightapi.io/airline"
_DATE_RE = re.compile(r"^\d{8}$")


class FlightClient:
    """Cached, validated client over FlightAPI's flight-number tracking endpoint."""

    def __init__(self, *, api_key: str, cache: FlightCache, settings: Settings) -> None:
        self._api_key = api_key
        self._cache = cache
        self._settings = settings
        self._http: httpx.AsyncClient | None = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def track(self, num: str, name: str, date: str, depap: str | None = None) -> FlightStatus:
        """Look up flight status for flight ``name+num`` on ``date`` (``YYYYMMDD``).

        Serves from the on-disk cache when a fresh entry exists; otherwise calls FlightAPI, caches
        the raw response per :func:`~.cache.resolve_ttl`, and returns the parsed status. Raises
        :class:`SelfCorrectionError` (lazily imported — see module-level import note) on a
        malformed ``date``, a missing API key, or a non-2xx FlightAPI response, so the agent's
        tool wrapper turns it into a corrective hint instead of crashing the turn.
        """
        # Lazy import: avoids src.integrations (loaded early, e.g. by build_context) pulling in
        # the whole src.agent package (heavy: langgraph/temporalio) just for this exception type.
        from src.agent.exceptions import SelfCorrectionError

        if not self._api_key:
            raise SelfCorrectionError(
                "FlightAPI ключ не настроен (KKR_FLIGHTAPI_KEY) — отслеживание рейсов недоступно."
            )
        if not _DATE_RE.fullmatch(date):
            raise SelfCorrectionError(f"'date' должен быть в формате YYYYMMDD, получено: {date!r}")

        key = self._cache.key_for(num, name, date, depap)
        cached = await self._cache.get_json(key)
        if cached is not None:
            status = self._try_parse(cached)
            if status is not None:
                return status
            log.warning("flight_client.cache_corrupt", key=key)

        payload = await self._fetch(num, name, date, depap)
        status = self._parse(payload)

        departure_dt = status.departure.departure_date_time if status.departure else None
        ttl = resolve_ttl(
            departure_dt,
            datetime.now(UTC),
            force_ttl=self._settings.flight_cache_force_ttl_seconds,
            far_seconds=self._settings.flight_ttl_far_seconds,
            near_seconds=self._settings.flight_ttl_near_seconds,
            far_boundary_days=self._settings.flight_ttl_far_boundary_days,
            near_boundary_days=self._settings.flight_ttl_near_boundary_days,
        )
        await self._cache.set_json(key, payload, ttl)
        return status

    def _try_parse(self, payload: Any) -> FlightStatus | None:
        try:
            return self._parse(payload)
        except ValidationError:
            return None

    def _parse(self, payload: Any) -> FlightStatus:
        departure: DepartureInfo | None = None
        arrival: ArrivalInfo | None = None
        raw: dict = {}
        items = payload if isinstance(payload, list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            if "departure" in item and departure is None:
                departure = DepartureInfo.model_validate(item["departure"])
                raw["departure"] = item["departure"]
            elif "arrival" in item and arrival is None:
                arrival = ArrivalInfo.model_validate(item["arrival"])
                raw["arrival"] = item["arrival"]
        return FlightStatus(departure=departure, arrival=arrival, raw=raw)

    async def _fetch(self, num: str, name: str, date: str, depap: str | None) -> Any:
        # Lazy import — see the note in track().
        from src.agent.exceptions import SelfCorrectionError

        url = f"{_BASE_URL}/{self._api_key}"
        params: dict[str, str] = {"num": num, "name": name, "date": date}
        if depap:
            params["depap"] = depap
        try:
            resp = await self._client().get(url, params=params)
        except httpx.HTTPError as exc:
            raise SelfCorrectionError(f"Не удалось связаться с FlightAPI: {exc}") from exc
        if resp.status_code != 200:
            raise SelfCorrectionError(
                f"FlightAPI вернул ошибку {resp.status_code} для рейса {name}{num} от {date}."
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise SelfCorrectionError(f"FlightAPI вернул нераспознаваемый ответ: {exc}") from exc
