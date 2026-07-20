"""Agent tools, grouped by domain.

- :mod:`booking` — recording booking details (``set_booking_info``) + booking-field helpers.
- :mod:`flights` — flight-status lookup via FlightAPI (``track_flight``).
- :mod:`mail` — composing and sending the letter / replies (``send_wishes_to_hotel``,
  ``reply_to_hotel``).
- :mod:`narration` — user-facing narration / control (``inform_step``, ``cancel_task``).
- :mod:`scheduling` — scheduled agent turns via Temporal Schedules (``set_scheduled_task``,
  ``list_scheduled_tasks``, ``update_scheduled_task``, ``cancel_scheduled_task``).
- :mod:`search` — web search tools (``search_internet``, ``extract_web_page``).
- :mod:`utils` — shared tool helpers.

Tools that mutate the graph state return a :class:`langgraph.types.Command(update=...)`; a bare
``dict`` return would be treated as the ``ToolMessage`` content by ``ToolNode`` and would *not*
update state. Non-serializable dependencies are fetched via :func:`src.context.get_context`
inside the tool so the runtime :class:`EmailContext` stays serializable.
"""

from .booking import set_booking_info
from .flights import track_flight
from .mail import reply_to_hotel, send_wishes_to_hotel
from .narration import cancel_task, inform_step
from .scheduling import scheduling_tools
from .search import search_tools

__all__ = [
    "cancel_task",
    "inform_step",
    "reply_to_hotel",
    "scheduling_tools",
    "search_tools",
    "send_wishes_to_hotel",
    "set_booking_info",
    "tools",
    "track_flight",
]

#: All tools wired into the agent (hotel-conversation tools + scheduling + web search + flights).
tools = [
    set_booking_info,
    send_wishes_to_hotel,
    reply_to_hotel,
    inform_step,
    cancel_task,
    *scheduling_tools,
    *search_tools,
    track_flight,
]
