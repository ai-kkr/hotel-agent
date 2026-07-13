"""State schemas for the email-extraction graph.

The graph carries booking-extraction progress (``parsed_email``, ``hotel_email``, retry and
search counters) plus the user's wishes collected at the end. ``EmailState`` is the full
internal state; ``EmailInputState``/``EmailOutputState`` are the narrowed input/output views
used by individual nodes, and ``EmailToHotel*State`` describe the terminal
``get_user_intention`` step.
"""

from typing import Annotated, TypedDict

from src_v2.utils.validators import EmailOptional

from ...state import AgentState
from .schemas import ExtractedBookingSchema

__all__ = [
    "EmailInputState",
    "EmailOutputState",
    "EmailState",
    "EmailToHotelInputState",
    "EmailToHotelOutputState",
    "SendEmailToHotelInputState",
    "SendEmailToHotelOutputState",
]


def _last(_left, right):
    """Last-write-wins reducer for scalar state fields written from multiple nodes."""
    return right


class EmailInputState(TypedDict, total=False):
    email_body: str
    attempts: int
    search_rounds: int

    # email metadata
    from_: str | None
    reply_to: str | None
    in_reply_to: str | None
    subject: str | None


class EmailOutputState(AgentState, total=False):
    parsed_email: Annotated[ExtractedBookingSchema | None, _last]
    hotel_email: Annotated[EmailOptional | None, _last]
    wishes: Annotated[list[str], _last]
    letter: Annotated[str | None, _last]
    error: Annotated[str | None, _last]
    attempts: Annotated[int, _last]
    search_rounds: Annotated[int, _last]
    cancelled: Annotated[bool | None, _last]
    intention_attempts: Annotated[int, _last]


class EmailState(AgentState, total=False):
    email_body: str
    parsed_email: Annotated[ExtractedBookingSchema | None, _last]
    hotel_email: Annotated[EmailOptional | None, _last]
    wishes: Annotated[list[str], _last]
    letter: Annotated[str | None, _last]
    error: Annotated[str | None, _last]
    attempts: Annotated[int, _last]
    search_rounds: Annotated[int, _last]
    cancelled: Annotated[bool | None, _last]
    intention_attempts: Annotated[int, _last]

    # email metadata
    from_: str | None
    reply_to: str | None
    in_reply_to: str | None
    subject: str | None


class EmailToHotelInputState(TypedDict):
    email_body: str
    hotel_email: EmailOptional


class EmailToHotelOutputState(TypedDict):
    hotel_email: EmailOptional
    wishes: list[str]


class SendEmailToHotelInputState(TypedDict, total=False):
    hotel_email: EmailOptional
    wishes: list[str]
    parsed_email: ExtractedBookingSchema
    original_subject: str
    request_id: str
    #
    from_: str


class SendEmailToHotelOutputState(TypedDict, total=False):
    hotel_email: EmailOptional
    wishes: list[str]
    parsed_email: ExtractedBookingSchema
    letter: str
