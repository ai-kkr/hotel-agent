"""FlightAPI integration: a cached, validated client for flight-status tracking.

- :mod:`models` — tolerance-oriented pydantic response models (``FlightStatus``).
- :mod:`cache` — on-disk async cache (cashews DiskCache backend) + TTL policy (``resolve_ttl``).
- :mod:`client` — :class:`FlightClient`, an ``httpx``-based client over the FlightAPI tracking
  endpoint, wired onto ``ApplicationContext`` like ``tavily_client``.
"""

from .client import FlightClient
from .models import ArrivalInfo, DepartureInfo, FlightStatus

__all__ = ["ArrivalInfo", "DepartureInfo", "FlightClient", "FlightStatus"]
