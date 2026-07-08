"""Read-only agent tools and their web backends.

Tools are strictly read-only (design D3): the agent may search the web, but has **no**
``send_email`` tool — side-effects are emitted as intents and executed by the workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx
from langchain_core.tools import BaseTool, StructuredTool


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearcher(Protocol):
    async def search(self, query: str) -> list[SearchResult]: ...


class WebFetcher(Protocol):
    async def fetch(self, url: str) -> str: ...


class FakeWebSearcher:
    """In-memory searcher for tests."""

    def __init__(self, results: dict[str, list[SearchResult]] | None = None) -> None:
        self._results = results or {}
        self.queries: list[str] = []

    def add(self, query: str, results: list[SearchResult]) -> FakeWebSearcher:
        self._results[query.lower()] = results
        return self

    async def search(self, query: str) -> list[SearchResult]:
        self.queries.append(query)
        return self._results.get(query.lower(), [])


class FakeWebFetcher:
    """In-memory fetcher for tests."""

    def __init__(self, pages: dict[str, str] | None = None) -> None:
        self._pages = pages or {}
        self.fetches: list[str] = []

    def add(self, url: str, body: str) -> FakeWebFetcher:
        self._pages[url.lower()] = body
        return self

    async def fetch(self, url: str) -> str:
        self.fetches.append(url)
        return self._pages.get(url.lower(), "")


class HttpxWebSearcher:
    """Web search via a configurable JSON endpoint (e.g. a hosted search API)."""

    def __init__(self, *, endpoint: str, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._client = client

    async def search(self, query: str) -> list[SearchResult]:
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)
        try:
            resp = await client.get(
                self._endpoint,
                params={"q": query},
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
        finally:
            if owns:
                await client.aclose()
        return [
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                snippet=str(item.get("snippet", "")),
            )
            for item in data.get("results", [])
        ]


class HttpxWebFetcher:
    """Fetch a URL and return its text body."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch(self, url: str) -> str:
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
        finally:
            if owns:
                await client.aclose()


def format_search_results(results: list[SearchResult]) -> str:
    if not results:
        return "no results found"
    return "\n".join(f"- {r.title}\n  {r.url}\n  {r.snippet}" for r in results)


def build_tools(searcher: WebSearcher, fetcher: WebFetcher) -> list[BaseTool]:
    """Build the read-only LangChain tools bound to the given web backends."""

    async def web_search(query: str) -> str:
        """Search the web for current information about a topic (hotel details, contact).

        Args:
            query: The search query (2-10 words recommended).
        """
        return format_search_results(await searcher.search(query))

    async def fetch_url(url: str) -> str:
        """Fetch the text content of a URL (e.g. the hotel's website).

        Args:
            url: The absolute URL to fetch.
        """
        body = await fetcher.fetch(url)
        return body[:4000] if body else "empty page"

    return [
        StructuredTool.from_function(coroutine=web_search, name="web_search"),
        StructuredTool.from_function(coroutine=fetch_url, name="fetch_url"),
    ]
