"""Shared data types for the booking-corpus collector scripts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Candidate:
    """A normalized email candidate fetched from the mailbox."""

    sender: str
    subject: str
    date: datetime
    body: str


@dataclass(frozen=True)
class ClassifiedCandidate:
    """A :class:`Candidate` after the LLM classification pass."""

    candidate: Candidate
    is_hotel_confirmation: bool
    system: str
    confidence: float
    skip_reason: str | None


@dataclass(frozen=True)
class RunSummary:
    """Outcome of a corpus-collection run, for logging / tests."""

    candidates_found: int
    confirmed: int
    skipped: int
    unique_systems: int
    selected: int
    written_files: list[str]
