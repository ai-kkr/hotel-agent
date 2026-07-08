"""Persist the selected corpus as ``.eml`` files + a ``manifest.json`` (design D5/D6)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from scripts.forward import pick_wish, wrap_as_forward
from scripts.types import ClassifiedCandidate


@dataclass(frozen=True)
class WriteResult:
    """Outcome of writing a corpus to disk."""

    written_files: list[str]
    unique_systems: int


def write_corpus(
    selected: list[ClassifiedCandidate],
    *,
    out_dir: Path,
    client_email: str,
    recipient: str,
    wishes_mode: str,
) -> WriteResult:
    """Write each selected confirmation as a forward ``.eml`` plus ``manifest.json``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries: list[dict[str, object]] = []
    written: list[str] = []

    for index, item in enumerate(selected, start=1):
        wish = pick_wish(index - 1, mode=wishes_mode)
        msg = wrap_as_forward(item, client_email=client_email, recipient=recipient, wish_cover=wish)
        filename = f"booking-{index:03d}.eml"
        path = out_dir / filename
        _write_eml(path, msg)
        written.append(str(path))
        manifest_entries.append(_manifest_entry(item, filename, wish))

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest_entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return WriteResult(written_files=written, unique_systems=len({e["system"] for e in manifest_entries}))


def _write_eml(path: Path, msg: EmailMessage) -> None:
    with path.open("wb") as fh:
        fh.write(bytes(msg))


def _manifest_entry(item: ClassifiedCandidate, filename: str, wish: str | None) -> dict[str, object]:
    candidate = item.candidate
    return {
        "filename": filename,
        "system": item.system,
        "sender": candidate.sender,
        "subject": candidate.subject,
        "date": candidate.date.isoformat(),
        "confidence": item.confidence,
        "has_cover": wish is not None,
        "cover": wish,
    }
