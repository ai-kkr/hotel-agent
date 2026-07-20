"""Tolerance-oriented pydantic response models for the FlightAPI tracking endpoint.

FlightAPI's docs explicitly warn the schema is approximate ("some objects will have more
attributes; a new array might also be there"), so every field is ``Optional`` and both models use
``extra="allow"`` — unknown/extra fields never fail validation, they just aren't typed.

Only ``departureDateTime`` / ``arrivalDateTime`` are real ISO-8601 timestamps (with UTC offset);
the other ``*Time`` fields (``scheduledTime``, ``estimatedTime``, ``offGroundTime``, …) come back as
free-form display strings (e.g. ``"14:55, Jul 16"``) and are kept as ``str``.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

#: Shared config: accept/emit the API's camelCase field names (``departureDateTime``, …) while
#: keeping snake_case attribute names on the model; ``extra="allow"`` tolerates unknown fields.
_MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="allow")


class DepartureInfo(BaseModel):
    """The ``departure`` block of a FlightAPI tracking response."""

    model_config = _MODEL_CONFIG

    airport: str | None = None
    airport_city: str | None = None
    airport_code: str | None = None
    airport_country_code: str | None = None
    airport_slug: str | None = None
    terminal: str | None = None
    gate: str | None = None
    scheduled_time: str | None = None
    estimated_time: str | None = None
    off_ground_time: str | None = None
    out_gate_time: str | None = None
    departure_date_time: datetime | None = None


class ArrivalInfo(BaseModel):
    """The ``arrival`` block of a FlightAPI tracking response."""

    model_config = _MODEL_CONFIG

    airport: str | None = None
    airport_city: str | None = None
    airport_code: str | None = None
    airport_country_code: str | None = None
    airport_slug: str | None = None
    terminal: str | None = None
    gate: str | None = None
    baggage: str | None = None
    scheduled_time: str | None = None
    estimated_time: str | None = None
    on_ground_time: str | None = None
    in_gate_time: str | None = None
    time_remaining: str | None = None
    arrival_date_time: datetime | None = None


class FlightStatus(BaseModel):
    """Flattened view of the FlightAPI ``[{"departure": …}, {"arrival": …}]`` response array.

    The departure-vs-arrival distinction is known by the calling agent from conversational
    context, so both blocks are returned (rather than a discriminated union — the raw payload has
    no discriminator field to key off).
    """

    departure: DepartureInfo | None = None
    arrival: ArrivalInfo | None = None
    #: The original, unmodified payload — preserved for debugging / agent curiosity, and as the
    #: escape hatch for fields the typed models don't (yet) know about.
    raw: dict = {}
