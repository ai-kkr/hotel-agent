"""Ad-hoc experiment: fetch real flight status via the FlightAPI integration (track_flight's
underlying client), for manual poking outside the agent/Telegram flow.

Usage:
    uv run python experiments/flightapi_test.py [FLIGHT] [DATE]
    uv run python experiments/flightapi_test.py SU1471                # today
    uv run python experiments/flightapi_test.py SU1471 20260722       # specific date

FLIGHT is airline code + number, with or without a space ("SU1471" / "SU 1471"). Defaults to
flight SU1471 on today's date (YYYYMMDD). Requires KKR_FLIGHTAPI_KEY in `.env` (get a key at
https://flightapi.io) — see `.env.example`.
"""

import asyncio
import re
import sys
from datetime import datetime

from src.agent.exceptions import SelfCorrectionError
from src.config import get_settings
from src.integrations.flights.cache import FlightCache
from src.integrations.flights.client import FlightClient
from src.integrations.flights.models import ArrivalInfo, DepartureInfo

_FLIGHT_RE = re.compile(r"^([A-Za-z]{2})\s*(\d+)$")


def _parse_flight(raw: str) -> tuple[str, str]:
    """Split "SU1471" / "SU 1471" into (airline_code, number); raises ValueError if malformed."""
    match = _FLIGHT_RE.match(raw.strip())
    if not match:
        raise ValueError(f"не удалось разобрать номер рейса: {raw!r} (ожидался вид 'SU1471')")
    code, num = match.groups()
    return code.upper(), num


def _print_leg(label: str, leg: DepartureInfo | ArrivalInfo | None) -> None:
    if leg is None:
        print(f"  {label}: нет данных")
        return
    print(
        f"  {label}: {leg.airport} ({leg.airport_code}), терминал {leg.terminal or '—'}, "
        f"гейт {leg.gate or '—'}, план {leg.scheduled_time or '—'}, "
        f"оценка/факт {leg.estimated_time or '—'}"
    )


async def main() -> None:
    flight = sys.argv[1] if len(sys.argv) > 1 else "SU1471"
    date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y%m%d")
    name, num = _parse_flight(flight)

    settings = get_settings()
    client = FlightClient(
        api_key=settings.flightapi_key,
        cache=FlightCache(settings.flight_cache_dir),
        settings=settings,
    )
    try:
        status = await client.track(num, name, date)
    except SelfCorrectionError as exc:
        print(f"Ошибка: {exc}")
        return
    finally:
        await client.aclose()

    print(f"Рейс {name}{num} на {date}:")
    _print_leg("Вылет", status.departure)
    _print_leg("Прилёт", status.arrival)
    print("\nПолный ответ:")
    print(status.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())

