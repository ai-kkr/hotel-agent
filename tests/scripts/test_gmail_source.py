from base64 import urlsafe_b64encode
from datetime import UTC, datetime

import pytest
from scripts.gmail_source import GmailAuthError, GmailSource


def _b64(text: str) -> str:
    return urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


class _FakeMessage:
    """Mimics ezgmail.GmailMessage: exposes headers-as-attrs + raw ``messageObj`` payload."""

    def __init__(
        self,
        sender: str,
        subject: str,
        body: str,
        ts: datetime,
        *,
        mime: str = "text/plain",
    ) -> None:
        self.sender = sender
        self.subject = subject
        self.timestamp = ts
        self.snippet = body[:80]
        self.messageObj = {
            "payload": {
                "mimeType": mime,
                "headers": [{"name": "Content-Type", "value": f"{mime}; charset=utf-8"}],
                "body": {"data": _b64(body)},
            }
        }


class _FakeThread:
    def __init__(self, message: _FakeMessage) -> None:
        self.messages = [message]


class _UnparseableThread:
    @property
    def messages(self) -> list:  # mimics ezgmail raising during lazy body decode
        raise UnicodeDecodeError("cp1251", b"\x98", 0, 1, "invalid")


class _FakeEzgmail:
    def __init__(
        self,
        threads: list[_FakeThread | _UnparseableThread] | None = None,
        raise_on_init: bool = False,
    ) -> None:
        self._threads = threads or []
        self._raise_on_init = raise_on_init
        self.init_called = False

    def init(self, *, tokenFile: str, credentialsFile: str) -> None:
        self.init_called = True
        if self._raise_on_init:
            raise RuntimeError("token revoked")

    def search(self, query: str, maxResults: int) -> list[_FakeThread | _UnparseableThread]:
        return self._threads[:maxResults]


class TestGmailSource:
    def test_search_returns_normalized_candidates(self) -> None:
        ts = datetime(2026, 1, 2, tzinfo=UTC)
        fake = _FakeEzgmail(
            [_FakeThread(_FakeMessage("a@b.com", "Booking", "body text", ts))]
        )
        source = GmailSource(credentials_path="c.json", token_path="t.json", client=fake)

        candidates = source.search("subject:booking", limit=5)

        assert len(candidates) == 1
        c = candidates[0]
        assert c.sender == "a@b.com"
        assert c.subject == "Booking"
        assert c.body == "body text"
        assert c.date == ts
        assert fake.init_called

    def test_auth_failure_raises_clear_error(self) -> None:
        fake = _FakeEzgmail(raise_on_init=True)
        source = GmailSource(credentials_path="c.json", token_path="t.json", client=fake)

        with pytest.raises(GmailAuthError) as exc:
            source.search("subject:booking", limit=5)
        assert "consent" in str(exc.value).lower()

    def test_unparseable_threads_are_skipped_not_fatal(self) -> None:
        ts = datetime(2026, 1, 2, tzinfo=UTC)
        fake = _FakeEzgmail(
            [
                _FakeThread(_FakeMessage("a@b.com", "Booking", "body", ts)),
                _UnparseableThread(),  # body decode fails inside ezgmail → skip
                _FakeThread(_FakeMessage("c@d.com", "Reservation", "body2", ts)),
            ]
        )
        source = GmailSource(credentials_path="c.json", token_path="t.json", client=fake)

        candidates = source.search("subject:booking", limit=5)

        assert [c.sender for c in candidates] == ["a@b.com", "c@d.com"]

    def test_html_only_body_is_converted_to_text(self) -> None:
        ts = datetime(2026, 1, 2, tzinfo=UTC)
        html = "<html><body><p>Booking at <b>Grand Hotel</b></p><p>Ref: ABC123</p></body></html>"
        fake = _FakeEzgmail([_FakeThread(_FakeMessage("a@b.com", "Booking", html, ts, mime="text/html"))])
        source = GmailSource(credentials_path="c.json", token_path="t.json", client=fake)

        candidates = source.search("subject:booking", limit=5)

        assert len(candidates) == 1
        body = candidates[0].body
        assert "Grand Hotel" in body
        assert "ABC123" in body
        assert "<html>" not in body.lower()  # HTML stripped
