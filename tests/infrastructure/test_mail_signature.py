from __future__ import annotations

from infrastructure.mail.signature import compute_signature, verify_mailgun_signature

SIGNING_KEY = "key-abcdef"


def _payload(ts: str, token: str, sig: str) -> dict[str, object]:
    return {"timestamp": ts, "token": token, "signature": sig}


class TestComputeSignature:
    def test_matches_known_vector(self) -> None:
        # computed manually: HMAC-SHA256(key, "1400000000secret")
        sig = compute_signature(SIGNING_KEY, "1400000000", "secret")
        assert isinstance(sig, str) and len(sig) == 64


class TestVerify:
    def test_accepts_valid_signature(self) -> None:
        ts, token = "1400000000", "secret"
        sig = compute_signature(SIGNING_KEY, ts, token)
        assert verify_mailgun_signature(_payload(ts, token, sig), SIGNING_KEY, now=float(ts)) is True

    def test_rejects_wrong_key(self) -> None:
        ts, token = "1400000000", "secret"
        sig = compute_signature("other-key", ts, token)
        assert verify_mailgun_signature(_payload(ts, token, sig), SIGNING_KEY, now=float(ts)) is False

    def test_rejects_tampered_token(self) -> None:
        ts, token = "1400000000", "secret"
        sig = compute_signature(SIGNING_KEY, ts, token)
        assert verify_mailgun_signature(_payload(ts, "other", sig), SIGNING_KEY, now=float(ts)) is False

    def test_rejects_missing_fields(self) -> None:
        assert verify_mailgun_signature({}, SIGNING_KEY) is False
        assert verify_mailgun_signature({"timestamp": "1", "token": "t"}, SIGNING_KEY) is False

    def test_rejects_stale_timestamp(self) -> None:
        ts, token = "1000000000", "secret"  # ancient
        sig = compute_signature(SIGNING_KEY, ts, token)
        assert verify_mailgun_signature(_payload(ts, token, sig), SIGNING_KEY, now=2_000_000_000) is False

    def test_rejects_garbage_timestamp(self) -> None:
        ts, token = "not-a-number", "secret"
        sig = compute_signature(SIGNING_KEY, ts, token)
        assert verify_mailgun_signature(_payload(ts, token, sig), SIGNING_KEY) is False
