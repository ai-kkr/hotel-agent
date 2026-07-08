"""LLM batch-classification of booking-confirmation candidates.

A single ``with_structured_output`` call over the whole candidate batch classifies each one
(``is_hotel_confirmation``, ``system``, ``confidence``) — one structured pass, no agent loop
(see design decision D2 of ``scripts-booking-corpus-collector``).
"""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from scripts.types import Candidate, ClassifiedCandidate

logger = logging.getLogger(__name__)


class CandidateClassification(BaseModel):
    """LLM verdict for a single candidate, mapped back by ``index``."""

    index: int = Field(description="0-based index of the candidate in the input list")
    is_hotel_confirmation: bool
    system: str | None = Field(
        default=None,
        description="Booking system or sender org, e.g. 'booking.com', 'marriott.com', 'independent hotel'",
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    skip_reason: str | None = Field(
        default=None,
        description="Why this is not a confirmation (only when is_hotel_confirmation is False)",
    )


class BatchClassification(BaseModel):
    """Wrapping schema so the whole batch is one structured response (one ``ainvoke``)."""

    items: list[CandidateClassification]


_SYSTEM_PROMPT = (
    "You classify email candidates from a personal inbox. For each candidate, decide whether it is a "
    "hotel BOOKING CONFIRMATION (a reservation confirmation / itinerary from a booking platform or a "
    "hotel), and identify the booking system or sender organization. Set confidence (0..1). If it is "
    "not a confirmation (e.g. marketing, receipts, cancellations of other services, flight tickets), "
    "set is_hotel_confirmation=false and give a short skip_reason. Return one item per candidate, "
    "keeping the original index."
)

_USER_HEADER = "Candidates (one per block, indexed):\n\n"


class ConfirmationClassifier:
    """Classify a batch of candidates with a single structured-output call."""

    def __init__(self, model: BaseChatModel, *, confidence_threshold: float = 0.6) -> None:
        # ``method="function_calling"`` mirrors the production extractor — the default JSON-schema
        # path breaks on OpenAI-compatible providers.
        self._structured = model.with_structured_output(BatchClassification, method="function_calling")
        self._threshold = confidence_threshold

    async def classify(self, candidates: list[Candidate]) -> list[ClassifiedCandidate]:
        if not candidates:
            return []
        raw = await self._structured.ainvoke(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _render_candidates(candidates)},
            ]
        )
        batch = raw if isinstance(raw, BatchClassification) else BatchClassification.model_validate(raw)
        return _merge(candidates, batch, self._threshold)


def _render_candidates(candidates: list[Candidate]) -> str:
    blocks: list[str] = []
    for idx, candidate in enumerate(candidates):
        blocks.append(
            f"[{idx}]\nFrom: {candidate.sender}\nSubject: {candidate.subject}\nBody:\n{candidate.body}"
        )
    return _USER_HEADER + "\n\n".join(blocks)


def _merge(
    candidates: list[Candidate], batch: BatchClassification, threshold: float
) -> list[ClassifiedCandidate]:
    verdicts: dict[int, CandidateClassification] = {item.index: item for item in batch.items}
    merged: list[ClassifiedCandidate] = []
    for idx, candidate in enumerate(candidates):
        verdict = verdicts.get(idx)
        if verdict is None:
            logger.warning("classifier omitted index %d; skipping", idx)
            continue
        confirmed = verdict.is_hotel_confirmation and verdict.confidence >= threshold
        system = (verdict.system or _domain_of(candidate.sender) or "unknown").strip()
        skip = None if confirmed else (verdict.skip_reason or "below threshold or not a confirmation")
        if not confirmed:
            logger.info("skipped [%d] %r: %s", idx, candidate.subject, skip)
        merged.append(
            ClassifiedCandidate(
                candidate=candidate,
                is_hotel_confirmation=confirmed,
                system=system,
                confidence=verdict.confidence,
                skip_reason=skip,
            )
        )
    return merged


def _domain_of(sender: str) -> str | None:
    """Best-effort sender domain for diversity grouping when the LLM gave no system."""
    address = sender.strip()
    if "<" in address and ">" in address:
        address = address[address.find("<") + 1 : address.find(">")]
    if "@" not in address:
        return None
    domain = address.rsplit("@", 1)[1].lower()
    return domain or None
