"""Inbound webhook endpoints (per-provider).

Mailgun posts inbound mail to ``/webhooks/{provider}/inbound`` and delivery events to
``/webhooks/{provider}/status``. Each request is signature-verified, normalized to a neutral
:class:`InboundEmail`, dispatched to domain events, and forwarded to the workflow gateway.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from domain.errors import UnauthorizedSender, UnknownClientToken
from domain.events import ClientMessage, ConfirmForward, HotelReply, InboundEmail
from domain.ids import route
from infrastructure.logging import get_logger
from infrastructure.mail.signature import verify_mailgun_signature
from presentation.container import WebhookDeps, WebhookDepsDep

_log = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _form_to_dict(request: Request) -> dict[str, object]:
    form = await request.form()
    out: dict[str, object] = {}
    for key in form:
        values = form.getlist(key)
        out[key] = values[-1] if values else ""
    return out


def _verify_or_reject(provider: str, payload: dict[str, object], deps: WebhookDeps) -> None:
    if provider == "mailgun":
        if not deps.signing_key:
            raise HTTPException(status_code=503, detail="mailgun signing key not configured")
        if not verify_mailgun_signature(payload, deps.signing_key):
            raise HTTPException(status_code=401, detail="invalid mailgun signature")
        return
    if provider == "stub":
        # Local-run mode: the stub normalizer accepts the same payload shape without a signature,
        # so developers can emulate inbound mail with a plain POST. Never enabled in production.
        return
    raise HTTPException(status_code=404, detail=f"unknown provider: {provider}")


@router.post("/{provider}/inbound")
async def inbound(provider: str, request: Request, deps: WebhookDepsDep) -> dict[str, Any]:
    payload = await _form_to_dict(request)
    _verify_or_reject(provider, payload, deps)
    email: InboundEmail = deps.normalizer.parse(payload)
    events = await deps.dispatcher.dispatch(email)
    accepted = 0
    for event in events:
        match event:
            case ConfirmForward():
                try:
                    await deps.intake.handle(event)
                    accepted += 1
                except UnknownClientToken:
                    _log.info("intake.unknown_token", token=event.client_token)
                    continue  # misrouted / unknown token: ignore, don't create a booking
                except UnauthorizedSender as exc:
                    _log.warning("intake.unauthorized_sender", token=event.client_token, error=str(exc))
                    raise HTTPException(status_code=403, detail=str(exc)) from exc
            case HotelReply():
                await deps.gateway.signal_hotel_reply(event)
                accepted += 1
            case ClientMessage():
                await deps.gateway.signal_client_message(event)
                accepted += 1
    _log.info("inbound.accepted", count=accepted, recipients=email.recipients)
    return {"accepted": accepted, "recipients": email.recipients}


@router.post("/{provider}/status")
async def status(provider: str, request: Request, deps: WebhookDepsDep) -> Response:
    payload = await _form_to_dict(request)
    _verify_or_reject(provider, payload, deps)
    # Delivery events: route a permanent bounce on a booking-scoped address to the workflow.
    event_type = str(payload.get("event", ""))
    severity = str(payload.get("severity", ""))
    recipient = str(payload.get("recipient", ""))
    local, _, _ = recipient.partition("@")
    routed = route(local)
    if (
        routed.is_conversation
        and routed.booking_id
        and event_type in {"bounced", "dropped", "failed"}
        and severity == "permanent"
    ):
        await deps.gateway.signal_delivery_failure(
            routed.booking_id, severity, str(payload.get("error", event_type))
        )
    return Response(status_code=204)
