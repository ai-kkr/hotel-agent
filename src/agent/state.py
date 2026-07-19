"""State schema for the hotel-conversation ReAct agent.

Extends :class:`langchain.agents.AgentState` (which provides ``messages``) with the agent's
working fields: booking details collected incrementally via ``set_booking_info``, the user's
wishes to forward, the last question asked to the user, the search-round counter written by the
shared search tools, and the cancellation flag set by ``cancel_task``.

Booking fields use the :func:`booking_field` reducer so that ``set_booking_info`` can send all
fields every call while omitted ones (``None``) leave the existing value untouched.
"""

from typing import Annotated

from langchain.agents import AgentState

__all__ = ["EmailState", "booking_field"]


def booking_field(left, right):
    """Reducer: keep the existing value when the update is ``None`` («don't change»).

    Lets ``set_booking_info`` write all five booking fields in one ``Command(update=...)`` while
    omitted ones are no-ops rather than overwrites.
    """
    return left if right is None else right


class EmailState(AgentState, total=False):
    # Booking details — filled incrementally; None means «leave unchanged».
    hotel_name: Annotated[str | None, booking_field]
    from_date: Annotated[str | None, booking_field]
    to_date: Annotated[str | None, booking_field]
    hotel_email: Annotated[str | None, booking_field]
    guests: Annotated[list[str] | None, booking_field]
    hotel_language: Annotated[str | None, booking_field]  # "ru" | "zh" | "en"
    #: Booking reference / confirmation number, if the confirmation carries one. Optional — not
    #: every voucher has a code; when present it goes into the email subject and the letter body.
    booking_ref: Annotated[str | None, booking_field]

    #: IANA timezone of the guest's home (e.g. "Europe/Moscow") — anchors scheduled-task times the
    #: guest expresses in their home zone. Set via ``set_booking_info``; read by the scheduling tools.
    home_timezone: Annotated[str | None, booking_field]
    #: IANA timezone of the trip / hotel (e.g. "Asia/Shanghai") — anchors scheduled-task times the
    #: guest expresses in the destination zone. Set via ``set_booking_info``; read by the scheduling tools.
    trip_timezone: Annotated[str | None, booking_field]

    user_wishes: list[str]
    user_question: str | None
    task_cancelled: bool
    search_rounds: int

    # Email threading for the hotel conversation.
    last_outbound_message_id: str | None  # Message-ID of the agent's last sent email
    last_hotel_message_id: str | None  # Message-ID of the hotel's last email (to reply to)
    last_hotel_subject: str | None  # subject of the hotel's last email (for "Re:")
