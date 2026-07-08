"""Local-only debug endpoints (never wired in production).

These exist so a developer running the stub mail stack can inspect what the system "sent" without a
real mail provider. ``GET /_local/outbox`` returns the recorded outbound emails (subject + body).
The endpoint is a no-op (404) unless a stub outbox is attached to ``app.state``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/_local", tags=["local-debug"], include_in_schema=False)


@router.get("/outbox")
async def outbox(request: Request) -> dict[str, Any]:
    gateway = getattr(request.app.state, "outbox_gateway", None)
    if gateway is None:
        raise HTTPException(status_code=404, detail="no stub outbox attached (production / not local)")
    records = list(gateway.outbox)
    return {
        "count": len(records),
        "messages": [
            {
                "message_id": r.message_id,
                "booking_id": r.booking_id,
                "to": r.to.value,
                "sender": r.sender.value,
                "reply_to": r.reply_to.value,
                "subject": r.subject,
                "body": r.body,
                "idempotency_key": r.idempotency_key,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ],
    }
