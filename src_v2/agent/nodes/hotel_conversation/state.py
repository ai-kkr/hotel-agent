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

    user_wishes: list[str]
    user_question: str | None
    task_cancelled: bool
    search_rounds: int

    # Email threading for the hotel conversation.
    last_outbound_message_id: str | None  # Message-ID of the agent's last sent email
    last_hotel_message_id: str | None  # Message-ID of the hotel's last email (to reply to)
    last_hotel_subject: str | None  # subject of the hotel's last email (for "Re:")
