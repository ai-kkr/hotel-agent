"""Flight-tracking agent tool (FlightAPI-backed)."""

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

from src.logging import get_logger

from ..context import EmailContext
from ..state import EmailState

__all__ = ["track_flight"]

log = get_logger(__name__)


@tool
async def track_flight(
    num: str,
    name: str,
    date: str,
    runtime: ToolRuntime[EmailContext, EmailState],
    depap: str | None = None,
):
    """Look up real-time flight status (departure and arrival legs) via FlightAPI.

    Use this to answer the guest's questions about their flight (gate, delay, ETA) or as part of
    a flight check you scheduled yourself (see set_scheduled_task — book checks around -7d / -1d /
    day-of). The tool returns both the departure and arrival blocks; decide from conversational
    context which one the guest cares about.

    Args:
        num: The flight number, without the airline code (e.g. "1842").
        name: The airline's IATA code (e.g. "SU", "DL").
        date: The flight's date, format YYYYMMDD (e.g. "20260815").
        depap: Optional departure airport code — only needed when two flights share the same
            number but depart from different airports.
    """
    log.info("tool.track_flight", num=num, name=name, date=date, depap=depap)
    from src.context import get_context  # lazy: avoids a context↔tools import cycle

    client = get_context().flight_client
    status = await client.track(num, name, date, depap)
    log.info("tool.track_flight.done", num=num, name=name, date=date)
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=(
                        f"Flight status for {name}{num} on {date}:\n"
                        f"{status.model_dump_json(exclude={'raw'})}"
                    ),
                    tool_call_id=runtime.tool_call_id,
                ),
            ],
        }
    )
