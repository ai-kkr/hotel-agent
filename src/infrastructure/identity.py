"""Identity token generation (infrastructure concern: uses ``secrets``)."""

from __future__ import annotations

import secrets

from domain.entities import Client
from domain.ids import ClientToken


def generate_client_token() -> ClientToken:
    """An unguessable client token (hex of :attr:`Client.TOKEN_BYTES` random bytes)."""
    return secrets.token_hex(Client.TOKEN_BYTES)
