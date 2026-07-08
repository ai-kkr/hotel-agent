"""Gmail access for the booking-corpus collector.

Wraps :mod:`ezgmail` (OAuth Desktop credential, browser login once, no 2FA) behind a thin,
injectable interface so tests never touch the real Gmail API. Search uses Gmail's native
operators via ``ezgmail.search`` (the same engine as the Gmail UI ``q`` box).
"""

from __future__ import annotations

import base64
import logging
import sys
from typing import TYPE_CHECKING, Any, Protocol

from scripts.types import Candidate

if TYPE_CHECKING:
    import types

logger = logging.getLogger(__name__)


class GmailAuthError(RuntimeError):
    """Raised when Gmail authentication / consent fails or the token is revoked."""


class CorpusSource(Protocol):
    """A source of candidate emails."""

    def search(self, query: str, *, limit: int) -> list[Candidate]:
        """Return up to ``limit`` candidates matching the Gmail search ``query``."""


class GmailSource:
    """Reads candidates from the owner's personal Gmail via :mod:`ezgmail`.

    ``client`` is injectable for tests (a fake module mimicking the ``ezgmail`` shape); when
    omitted, the real :mod:`ezgmail` is imported lazily so importing this module never requires
    the dependency.
    """

    def __init__(
        self,
        *,
        credentials_path: str,
        token_path: str,
        auth_port: int = 8411,
        client: Any | None = None,
    ) -> None:
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._auth_port = auth_port
        self._client = client

    def search(self, query: str, *, limit: int) -> list[Candidate]:
        logger.info("searching Gmail: query=%r limit=%d", query, limit)
        ezgmail = self._load_client()
        # ``ezgmail.init`` -> ``oauth2client.tools.run_flow`` parses ``sys.argv`` with a STRICT
        # argparser. Two problems to neutralize:
        #   1. Our own CLI flags (--client-email, --recipient, ...) would make it SystemExit.
        #   2. Its default callback port is 8080 — which collides with the project's temporal-ui
        #      container (docker-compose maps 8080:8080). OrbStack/Docker intercepts localhost:8080,
        #      so Google's post-consent redirect lands on the Temporal UI instead of our callback,
        #      and token.json is never written. We pin a free port (default 8411).
        saved_argv = sys.argv
        sys.argv = [saved_argv[0], "--auth_host_port", str(self._auth_port)]
        try:
            # Only treat init/consent failures as auth errors — a search() TypeError or API error
            # must surface as itself, not masquerade as "token revoked".
            try:
                ezgmail.init(tokenFile=self._token_path, credentialsFile=self._credentials_path)
            except GmailAuthError:
                raise
            except Exception as exc:
                msg = (
                    "Gmail access failed (token may be missing, expired, or revoked). "
                    "Re-run to repeat the browser consent flow, or check your credentials file."
                )
                raise GmailAuthError(msg) from exc
            threads = ezgmail.search(query, maxResults=limit)
        finally:
            sys.argv = saved_argv
        logger.info("gmail returned %d threads", len(threads))
        return self._to_candidates(threads)

    def _to_candidates(self, threads: list[Any]) -> list[Candidate]:
        # ezgmail decodes each message body eagerly on ``thread.messages`` access, using the
        # charset declared in the email's Content-Type. Some real emails declare a charset
        # (e.g. cp1251) but carry bytes that don't decode under it -> UnicodeDecodeError from
        # inside ezgmail. Skip those threads with a warning rather than aborting the whole run.
        total = len(threads)
        candidates: list[Candidate] = []
        skipped = 0
        for index, thread in enumerate(threads, start=1):
            try:
                candidate = self._to_candidate(thread)
            except Exception as exc:  # best-effort per-thread resilience.
                skipped += 1
                logger.warning("skipped unparseable thread %d/%d: %s", index, total, exc)
                continue
            candidates.append(candidate)
            if index % 10 == 0 or index == total:
                logger.info("parsing threads: %d/%d (ok=%d, skipped=%d)", index, total, len(candidates), skipped)
        logger.info("parsed %d candidates, skipped %d unparseable", len(candidates), skipped)
        return candidates

    def _load_client(self) -> types.ModuleType | Any:
        if self._client is not None:
            return self._client
        import ezgmail  # lazy import: keeps the dev dep out of test collection.

        return ezgmail

    @staticmethod
    def _to_candidate(thread: Any) -> Candidate:
        message = thread.messages[0]
        return Candidate(
            sender=getattr(message, "sender", "") or "",
            subject=getattr(message, "subject", "") or "",
            date=getattr(message, "timestamp", None) or _epoch(),
            body=_extract_body(message),
        )


def _extract_body(message: Any) -> str:
    """Best-effort plaintext body, HTML-aware and charset-resilient.

    Walks the raw Gmail ``payload`` (``message.messageObj``) ourselves rather than trusting
    ``ezgmail``'s eager decode: prefer a ``text/plain`` part, fall back to ``text/html``
    (converted to text), and decode with ``errors="replace"`` so a wrong/strict charset never
    crashes us. Last resort: the always-present ``snippet``.
    """
    payload = getattr(message, "messageObj", {}).get("payload") or {}
    plain = _find_part(payload, "text/plain")
    if plain is not None:
        return _decode_part(*plain)
    html = _find_part(payload, "text/html")
    if html is not None:
        return _html_to_text(_decode_part(*html))
    snippet = getattr(message, "snippet", "") or ""
    return _html_to_text(snippet) if _looks_like_html(snippet) else snippet


def _find_part(payload: Any, target_mime: str) -> tuple[str, str, str | None] | None:
    """Depth-first search for the first part with ``target_mime`` carrying body data.

    Returns ``(mime, base64url_data, charset)`` or ``None``.
    """
    mime = str(payload.get("mimeType", "")).lower()
    data = (payload.get("body") or {}).get("data")
    if mime == target_mime and data:
        return mime, data, _charset_of(payload.get("headers") or [])
    for part in payload.get("parts") or []:
        found = _find_part(part, target_mime)
        if found is not None:
            return found
    return None


def _decode_part(_mime: str, data: str, charset: str | None) -> str:
    # Gmail sends body data as URL-safe base64 without guaranteed padding.
    padded = data + "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(padded)
    return raw.decode(charset or "utf-8", errors="replace")


def _charset_of(headers: list[dict[str, str]]) -> str | None:
    for header in headers:
        if header.get("name", "").lower() == "content-type":
            value = header.get("value", "")
            lower = value.lower()
            marker = lower.find("charset=")
            if marker != -1:
                charset = value[marker + len("charset=") :].split(";")[0].strip().strip('"')
                return charset or None
    return None


def _looks_like_html(text: str) -> bool:
    lowered = text.lower()
    return any(tag in lowered for tag in ("<html", "<body", "<div", "<table", "<p>", "<br"))


def _html_to_text(html: str) -> str:
    import html2text  # dev dependency

    converter = html2text.HTML2Text()
    converter.body_width = 0  # don't hard-wrap lines
    converter.ignore_images = True
    return converter.handle(html).strip()


def _epoch() -> Any:
    from datetime import UTC, datetime

    return datetime(1970, 1, 1, tzinfo=UTC)
