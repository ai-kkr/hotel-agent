import json
from datetime import UTC, datetime
from email import message_from_bytes
from pathlib import Path

from scripts.corpus_writer import write_corpus
from scripts.types import Candidate, ClassifiedCandidate


def _classified(system: str) -> ClassifiedCandidate:
    return ClassifiedCandidate(
        candidate=Candidate(
            sender=f"res@{system}",
            subject=f"Booking at {system}",
            date=datetime(2026, 3, 1, tzinfo=UTC),
            body=f"Confirmation from {system}",
        ),
        is_hotel_confirmation=True,
        system=system,
        confidence=0.9,
        skip_reason=None,
    )


class TestWriteCorpus:
    def test_writes_eml_files_and_manifest(self, tmp_path: Path) -> None:
        selected = [_classified("marriott.com"), _classified("booking.com")]
        result = write_corpus(
            selected,
            out_dir=tmp_path,
            client_email="me@x.com",
            recipient="c.t@kkr-hotel.com",
            wishes_mode="none",
        )

        assert len(result.written_files) == 2
        assert (tmp_path / "booking-001.eml").exists()
        assert (tmp_path / "booking-002.eml").exists()
        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        assert [e["system"] for e in manifest] == ["marriott.com", "booking.com"]
        assert all(e["has_cover"] is False for e in manifest)
        assert result.unique_systems == 2

    def test_manifest_has_cover_flag(self, tmp_path: Path) -> None:
        result = write_corpus(
            [_classified("marriott.com")],
            out_dir=tmp_path,
            client_email="me@x.com",
            recipient="c.t@k.com",
            wishes_mode="mixed",
        )
        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        # index 0 in mixed mode → first pool entry is "" → no cover
        assert manifest[0]["has_cover"] is (manifest[0]["cover"] is not None)
        assert len(result.written_files) == 1

    def test_eml_is_valid_forward(self, tmp_path: Path) -> None:
        write_corpus(
            [_classified("marriott.com")],
            out_dir=tmp_path,
            client_email="me@x.com",
            recipient="c.t@k.com",
            wishes_mode="none",
        )
        parsed = message_from_bytes((tmp_path / "booking-001.eml").read_bytes())
        assert parsed["To"] == "c.t@k.com"
        assert "-----Original Message-----" in parsed.get_payload()
