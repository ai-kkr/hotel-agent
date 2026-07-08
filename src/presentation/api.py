"""Client-facing API (spec 8.4).

``POST /api/client-message`` is a channel-agnostic inbound path: any source (native app, an
integration) can submit a client follow-up, normalized into a :class:`ClientMessage` and signaled
to the booking workflow. This is the seed of omnichannel inbound (spec 8.5) alongside the email
adapter.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from domain.enums import Channel
from domain.events import ClientMessage
from presentation.container import WebhookDepsDep

router = APIRouter(prefix="/api", tags=["client"])


class ClientMessageIn(BaseModel):
    booking_id: str = Field(description="The booking the follow-up pertains to")
    body: str = Field(min_length=1)
    channel: Literal["email", "telegram", "whatsapp", "native_app", "api"] = "api"


@router.post("/client-message")
async def client_message(payload: ClientMessageIn, deps: WebhookDepsDep) -> dict[str, Any]:
    event = ClientMessage(
        booking_id=payload.booking_id,
        body=payload.body,
        received_at=datetime.now(tz=UTC),
        channel=Channel(payload.channel),
    )
    try:
        await deps.gateway.signal_client_message(event)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"could not signal workflow: {exc}") from exc
    return {"accepted": True, "booking_id": payload.booking_id}


class ClientMailboxIn(BaseModel):
    """A bot-facing request to resolve/create a client's private mailbox (design D10)."""

    channel: Literal["telegram", "whatsapp", "native_app"] = "telegram"
    address: str = Field(min_length=1, description="Channel address, e.g. Telegram chat_id")


@router.post("/client-mailbox")
async def client_mailbox(
    payload: ClientMailboxIn, request: Request, deps: WebhookDepsDep
) -> dict[str, Any]:
    """Resolve or create a client's private intake mailbox (bot → API, shared-secret auth).

    The bot (a separate process) calls this with ``KKR_BOT_API_SECRET`` to obtain the private
    ``c.<token>@`` address for a channel identity. The address is never shown to the user.
    """
    if not deps.settings.bot_api_secret:
        raise HTTPException(status_code=503, detail="bot api secret not configured")
    if _bot_secret_from_headers(request) != deps.settings.bot_api_secret:
        raise HTTPException(status_code=401, detail="invalid bot api secret")
    if deps.mailbox is None:
        raise HTTPException(status_code=503, detail="mailbox service not configured")
    try:
        address = await deps.mailbox.resolve_or_create(Channel(payload.channel), payload.address)
    except ValueError as exc:
        # channel address already bound to another client — surface as a conflict, not a 500.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"mailbox": address.value, "channel": payload.channel}


def _bot_secret_from_headers(request: Request) -> str:
    """Accept the shared secret in ``X-Bot-Secret`` or ``Authorization: Bearer <secret>``."""
    if request.headers.get("x-bot-secret"):
        return request.headers["x-bot-secret"]
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""
