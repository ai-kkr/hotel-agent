import asyncio

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

from src.logging import get_logger

from ..context import EmailContext
from ..state import EmailState

__all__ = ["search_tools"]

log = get_logger(__name__)


@tool
async def search_internet(
    query: str,
    runtime: ToolRuntime[EmailContext, EmailState],
):
    """Search the web for the given query to find information about a hotel.

    Use this to look up a hotel's contact email, official website, or other details when the
    forwarded booking confirmation does not include them. Returns a summary of search results.

    Args:
        query: A concise web search query (e.g. hotel name + "contact email").
    """
    log.info("tool.search_internet", query=query)
    from src.context import get_context  # lazy: avoids a context↔tools import cycle

    client = get_context().tavily_client
    res = await asyncio.to_thread(client.search, query)
    rounds = runtime.state.get("search_rounds", 0) + 1
    log.info("tool.search_internet.done", query=query, search_rounds=rounds)
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Search results for query '{query}':\n{res}",
                    tool_call_id=runtime.tool_call_id,
                ),
            ],
            "search_rounds": rounds,
        }
    )


@tool
async def extract_web_page(
    url: str,
    runtime: ToolRuntime[EmailContext, EmailState],
):
    """Fetch and extract the readable text content of a web page at the given URL.

    Use this after search_internet to read a specific page (e.g. the hotel's contact page) and find
    the contact email. Returns the extracted page text.

    Args:
        url: The absolute URL of the page to extract content from.
    """
    log.info("tool.extract_web_page", url=url)
    from src.context import get_context  # lazy: avoids a context↔tools import cycle

    client = get_context().tavily_client
    res = await asyncio.to_thread(client.extract, url)
    log.info("tool.extract_web_page.done", url=url)
    return res


search_tools = [extract_web_page, search_internet]
