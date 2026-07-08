"""Diverse selection: first-seen-per-system with fallback backfill (design D3)."""

from __future__ import annotations

from scripts.types import ClassifiedCandidate


def select_diverse(classified: list[ClassifiedCandidate], *, count: int) -> list[ClassifiedCandidate]:
    """Pick up to ``count`` candidates, preferring one per distinct system.

    First pass takes the first candidate of each system (round-robin by system). If there are
    fewer distinct systems than ``count``, the second pass backfills from the remaining
    confirmed candidates in original order.
    """
    if count <= 0:
        return []

    confirmed = [item for item in classified if item.is_hotel_confirmation]
    if not confirmed:
        return []

    chosen: list[ClassifiedCandidate] = []
    chosen_ids: set[int] = set()
    seen_systems: set[str] = set()

    for item in confirmed:
        if len(chosen) >= count:
            break
        if item.system in seen_systems:
            continue
        seen_systems.add(item.system)
        chosen.append(item)
        chosen_ids.add(id(item))

    if len(chosen) < count:
        for item in confirmed:
            if len(chosen) >= count:
                break
            if id(item) in chosen_ids:
                continue
            chosen.append(item)
            chosen_ids.add(id(item))

    return chosen
