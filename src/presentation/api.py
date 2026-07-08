"""Client-facing API (spec 8.4).

``POST /api/client-message`` is a channel-agnostic inbound path: any source (native app, an
integration) can submit a client follow-up, normalized into a :class:`ClientMessage` and signaled
to the booking workflow. This is the seed of omnichannel inbound (spec 8.5) alongside the email
adapter.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
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
