"""Factory wiring for the LangGraph/LangChain agents (spec 5.6).

The negotiator's per-booking context lives on the checkpoint saver (``thread_id = booking_id``).
Production passes a :class:`PostgresSaver`; tests pass an :class:`InMemorySaver`.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from domain.ports import (
    ConfirmationExtractor,
    ContactDiscoverer,
    NegotiationAgent,
    ReportBuilder,
)
from infrastructure.agents.discoverer import ContactDiscovererAgent
from infrastructure.agents.extractor import ConfirmationExtractorAgent
from infrastructure.agents.negotiator import NegotiationAgentImpl
from infrastructure.agents.reporter import ReportBuilderAgent
from infrastructure.agents.tools import WebFetcher, WebSearcher
from infrastructure.config import Settings


@dataclass(frozen=True)
class AgentBundle:
    extractor: ConfirmationExtractor
    discoverer: ContactDiscoverer
    negotiator: NegotiationAgent
    reporter: ReportBuilder


def build_agents(
    settings: Settings,
    *,
    model: BaseChatModel,
    checkpointer: BaseCheckpointSaver,
    searcher: WebSearcher,
    fetcher: WebFetcher,
) -> AgentBundle:
    """Construct all four agent implementations with shared collaborators."""
    return AgentBundle(
        extractor=ConfirmationExtractorAgent(
            model, confidence_threshold=settings.extraction_confidence_threshold
        ),
        discoverer=ContactDiscovererAgent(model, searcher, fetcher),
        negotiator=NegotiationAgentImpl(model, searcher, fetcher, checkpointer),
        reporter=ReportBuilderAgent(model),
    )
