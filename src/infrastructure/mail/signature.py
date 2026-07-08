"""Mailgun webhook signature verification.

Mailgun signs each webhook with an HMAC-SHA256 of ``timestamp + token`` using the account's
HTTP webhook signing key. We verify both the signature and that the timestamp is recent (replay
protection).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping

DEFAULT_MAX_AGE_SECONDS = 15 * 60  # reject webhooks older than 15 minutes


def compute_signature(signing_key: str, timestamp: str, token: str) -> str:
    """The expected Mailgun signature for the given timestamp/token."""
    return hmac.new(
        key=signing_key.encode(),
        msg=f"{timestamp}{token}".encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify_mailgun_signature(
    payload: Mapping[str, object],
    signing_key: str,
    *,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    now: float | None = None,
) -> bool:
    """Return True iff the payload's signature is valid and the timestamp is fresh."""
    timestamp = payload.get("timestamp")
    token = payload.get("token")
    signature = payload.get("signature")
    if not (isinstance(timestamp, str) and isinstance(token, str) and isinstance(signature, str)):
        return False

    expected = compute_signature(signing_key, timestamp, token)
    if not hmac.compare_digest(expected, signature):
        return False

    current = time.time() if now is None else now
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    return abs(current - ts) <= max_age_seconds
