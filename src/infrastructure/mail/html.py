"""HTML-aware body extraction for inbound mail normalizers (design D2).

Inbound providers (Mailgun, stub) expose both a plaintext part (``body-plain`` / ``stripped-text``)
and an HTML part (``body-html`` / ``stripped-html``). We prefer plaintext and fall back to
converting HTML via :mod:`html2text`, so an HTML-only booking confirmation still reaches the
extractor with a readable body instead of an empty one.

Both :class:`MailgunWebhookNormalizer` and :class:`StubInboundNormalizer` source the body through
:func:`extract_body_text` so the fallback order lives in exactly one place.
"""

from __future__ import annotations

from collections.abc import Mapping

import html2text


def html_to_text(html: str) -> str:
    """Convert HTML to readable plaintext (best-effort, resilient to malformed input).

    A fresh ``HTML2Text`` is created per call: the converter holds mutable state between
    ``handle()`` invocations, so reusing one instance leaks output across messages.
    """
    try:
        converter = html2text.HTML2Text()
        converter.body_width = 0  # don't hard-wrap lines
        converter.ignore_images = True
        return converter.handle(html).strip()
    except Exception:  # never let a bad HTML body abort inbound parsing.
        return ""


def _first(payload: Mapping[str, object], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def extract_body_text(payload: Mapping[str, object]) -> str:
    """Pick the inbound body: prefer plaintext, fall back to ``html2text`` of the HTML part."""
    plain = _first(payload, "body-plain", "stripped-text")
    if plain:
        return plain
    html = _first(payload, "body-html", "stripped-html")
    return html_to_text(html) if html else ""
