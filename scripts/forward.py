"""Forward re-wrapping (design D4, layer A+B).

Rebuilds a fetched confirmation as a client *forward* to ``c.<token>@<mail-domain>`` so the
full ``booking-intake`` chain (authentication, routing, forward/cover separation, extraction)
is exercised — not just the extractor. The ``-----Original Message-----`` convention matches
the production :class:`ConfirmationExtractor`, which separates the sender's cover note from
the forwarded block (see ``src/domain/application.py::_confirm_forward`` and
``src/infrastructure/agents/extractor.py``).
"""

from __future__ import annotations

from email.message import EmailMessage
from email.policy import SMTP
from email.utils import format_datetime

from scripts.types import ClassifiedCandidate

DEFAULT_WISH_COVERS: tuple[str, ...] = (
    "",
    "Please request a high floor if possible.",
    "Could you ask about a late check-out?",
    "I'd appreciate a quiet room away from the elevator.",
    "Please mention this is an anniversary trip — any welcome treat would be lovely.",
)


def wrap_as_forward(
    item: ClassifiedCandidate,
    *,
    client_email: str,
    recipient: str,
    wish_cover: str | None,
) -> EmailMessage:
    """Build a replay-ready forward ``.eml`` for one classified confirmation."""
    candidate = item.candidate
    msg = EmailMessage(policy=SMTP)
    msg["From"] = client_email
    msg["To"] = recipient
    msg["Subject"] = _forward_subject(candidate.subject)
    msg.set_content(_forward_body(candidate, wish_cover))
    return msg


def pick_wish(index: int, *, mode: str, pool: tuple[str, ...] = DEFAULT_WISH_COVERS) -> str | None:
    """Choose a cover-note wish for the ``index``-th selected email.

    ``mode``: ``"none"`` disables covers, ``"mixed"`` cycles through ``pool`` (which includes an
    empty entry → no cover). Deterministic by index so tests are stable.
    """
    if mode == "none" or not pool:
        return None
    if mode != "mixed":
        return None
    wish = pool[index % len(pool)]
    return wish or None


def _forward_subject(subject: str) -> str:
    stripped = subject.strip()
    if stripped.lower().startswith("fwd:"):
        return stripped
    return f"Fwd: {stripped}" if stripped else "Fwd: (no subject)"


def _forward_body(candidate: object, wish_cover: str | None) -> str:
    parts: list[str] = []
    if wish_cover:
        parts.append(wish_cover.strip())
        parts.append("")
    parts.append(_original_block(candidate))
    return "\n".join(parts)


def _original_block(candidate: object) -> str:
    sender = getattr(candidate, "sender", "") or ""
    subject = getattr(candidate, "subject", "") or ""
    date = getattr(candidate, "date", None)
    body = getattr(candidate, "body", "") or ""
    date_line = format_datetime(date) if date is not None else ""
    header = (
        "-----Original Message-----\n"
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        + (f"Date: {date_line}\n" if date_line else "")
        + "\n"
    )
    return header + body
