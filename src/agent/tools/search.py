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
    domain: str | None = None,
):
    """Search the web via Tavily to find a hotel's contact email, official website, or other
    details missing from the forwarded booking confirmation.

    This is a SEMANTIC search engine, NOT Google — it does not parse search operators. Write the
    query in natural language.

    RULES for the query:
    - NEVER use operators: `site:`, `OR`, `AND`, `NOT`. They are silently ignored and turn the
      query into noise. In particular, `site:example.com` does NOT restrict to that domain — use
      the `domain` argument instead.
    - Write a short natural-language question or phrase (< ~400 chars), e.g.
      "contact email for Flamingo Hotel Oludeniz" or "official website and booking email of
      Hotel X in Lisbon".
    - You MAY quote an exact phrase with double quotes, e.g. `"reservation@"`.
    - Keep it focused: one hotel, one intent per query.

    Args:
        query: A concise natural-language search query. No `site:` / boolean operators.
        domain: Optional bare domain (e.g. "flamingohoteloludeniz.com") to restrict results to
            that site only — this is the correct way to scope to a hotel's own website, since
            `site:` in the query is ignored. Omit for a general web search.
    """
    log.info("tool.search_internet", query=query, domain=domain)
    from src.context import get_context  # lazy: avoids a context↔tools import cycle

    client = get_context().tavily_client
    search_kwargs: dict = {"include_domains": [domain]} if domain else {}
    res = await asyncio.to_thread(client.search, query, **search_kwargs)
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
