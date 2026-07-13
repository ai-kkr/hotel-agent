"""Agent tools, grouped by domain.

- :mod:`booking` — recording booking details (``set_booking_info``) + booking-field helpers.
- :mod:`mail` — composing and sending the letter / replies (``send_wishes_to_hotel``,
  ``reply_to_hotel``).
- :mod:`narration` — user-facing narration / control (``inform_step``, ``cancel_task``).
- :mod:`search` — web search tools (``search_internet``, ``extract_web_page``).
- :mod:`utils` — shared tool helpers.

Tools that mutate the graph state return a :class:`langgraph.types.Command(update=...)`; a bare
``dict`` return would be treated as the ``ToolMessage`` content by ``ToolNode`` and would *not*
update state. Non-serializable dependencies are fetched via :func:`src.context.get_context`
inside the tool so the runtime :class:`EmailContext` stays serializable.
"""

from .booking import set_booking_info
from .mail import reply_to_hotel, send_wishes_to_hotel
from .narration import cancel_task, inform_step
from .search import search_tools

__all__ = [
    "cancel_task",
    "inform_step",
    "reply_to_hotel",
    "search_tools",
    "send_wishes_to_hotel",
    "set_booking_info",
    "tools",
]

#: All tools wired into the agent (hotel-conversation tools + web search).
tools = [
    set_booking_info,
    send_wishes_to_hotel,
    reply_to_hotel,
    inform_step,
    cancel_task,
    *search_tools,
]
