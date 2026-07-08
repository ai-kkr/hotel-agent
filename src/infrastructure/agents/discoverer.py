"""ContactDiscoverer (spec 5.3).

A ``create_agent`` ReAct agent with read-only web tools and ``response_format=ContactSchema``. It
finds the hotel contact email and correspondence language via the web, falling back to English.
"""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from domain.ids import EmailAddress
from domain.intents import SearchDone
from infrastructure.agents.schemas import ContactSchema
from infrastructure.agents.tools import WebFetcher, WebSearcher, build_tools

SYSTEM_PROMPT = """You find a hotel's contact EMAIL address and the language the hotel corresponds in.

Use web_search and fetch_url to investigate the hotel's website. Return the contact email and the
hotel's correspondence language (ISO-639-1, e.g. en, fr, es). If you cannot confidently find a
contact email, set `found` to false and leave `email` null. When unsure of the language, use "en"."""


class ContactDiscovererAgent:
    """Implements :class:`domain.ports.ContactDiscoverer`."""

    def __init__(self, model: BaseChatModel, searcher: WebSearcher, fetcher: WebFetcher) -> None:
        self._tools = build_tools(searcher, fetcher)
        self._agent = create_agent(
            model=model,
            tools=self._tools,
            system_prompt=SYSTEM_PROMPT,
            response_format=ContactSchema,
        )

    async def discover(self, hotel_name: str, hint_website: str | None) -> SearchDone:
        hint = f" Known website: {hint_website}." if hint_website else ""
        result = await self._agent.ainvoke(
            {
                "messages": [
                    {"role": "user", "content": f"Hotel: {hotel_name}.{hint} Find its contact email and language."}
                ]
            },
            config={"recursion_limit": 8},
        )
        schema = _coerce(result.get("structured_response"))
        email = (schema.email or "").strip()
        language = (schema.language or "en").strip().lower()[:2] or "en"
        return SearchDone(
            hotel_name=hotel_name,
            language=language,
            email=EmailAddress(email) if email else None,
            website=(schema.website or "").strip() or None,
            found=bool(email),
        )


def _coerce(raw: Any) -> ContactSchema:
    if isinstance(raw, ContactSchema):
        return raw
    if isinstance(raw, dict):
        return ContactSchema.model_validate(raw)
    return ContactSchema()
