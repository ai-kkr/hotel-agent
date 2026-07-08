from __future__ import annotations

from infrastructure.mail.html import extract_body_text, html_to_text


class TestHtmlToText:
    def test_converts_html_to_text_and_strips_tags(self) -> None:
        html = "<html><body><p>Booking at <b>Grand Hotel</b></p><p>Ref: ABC123</p></body></html>"
        text = html_to_text(html)
        assert "Grand Hotel" in text
        assert "ABC123" in text
        assert "<html>" not in text.lower()

    def test_handles_table_like_content(self) -> None:
        html = (
            "<table><tr><td>Check-in</td><td>2026-02-01</td></tr>"
            "<tr><td>Check-out</td><td>2026-02-04</td></tr></table>"
        )
        text = html_to_text(html)
        assert "Check-in" in text
        assert "2026-02-01" in text
        assert "Check-out" in text
        assert "2026-02-04" in text

    def test_malformed_html_does_not_raise(self) -> None:
        assert html_to_text("<p>unclosed <b>bold") is not None  # no exception
        assert "unclosed" in html_to_text("<p>unclosed <b>bold")


class TestExtractBodyText:
    def test_prefers_plain(self) -> None:
        payload = {"body-plain": "plain body", "body-html": "<p>html body</p>"}
        assert extract_body_text(payload) == "plain body"

    def test_falls_back_to_html_when_plain_empty(self) -> None:
        payload = {"body-plain": "", "body-html": "<p>Grand Hotel Ref ABC123</p>"}
        text = extract_body_text(payload)
        assert "Grand Hotel" in text
        assert "ABC123" in text
        assert "<p>" not in text

    def test_stripped_fields_used_as_fallback(self) -> None:
        payload = {"stripped-text": "stripped plain"}
        assert extract_body_text(payload) == "stripped plain"

    def test_stripped_html_fallback(self) -> None:
        payload = {"stripped-html": "<p>late checkout</p>"}
        assert "late checkout" in extract_body_text(payload)

    def test_both_empty_yields_empty(self) -> None:
        assert extract_body_text({}) == ""
        assert extract_body_text({"body-plain": "   ", "body-html": ""}) == ""
