"""Pydantic models for the Mailtrap **inbound** webhook payload.

The inbound OpenAPI spec does not describe the webhook body (it is only mentioned in prose), so
these models are written by hand from the documented event shape. Mailtrap signs every webhook
with HMAC-SHA256 in the ``Mailtrap-Signature`` header — verify it first with
``mailtrap.verify_signature(raw_body, signature, signing_secret)`` before parsing the JSON.

Example payload::

    {
      "events": [
        {
          "event": "inbound.message_received",
          "event_id": "27c34797-7c37-11f1-b788-0a58a9feac02",
          "timestamp": 1783671175722,
          "inbox_id": 250,
          "message_id": "1870314786754420736",
          "from": "Андрей Викторов <andvikt@gmail.com>"
        }
      ]
    }
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

# Known inbound webhook event types. The canonical live event is ``inbound.message_received``;
# the "Send Test Webhook" button in the Mailtrap panel posts ``inbound_message_received``
# (underscore) — accept both so the panel test passes too.
InboundWebhookEventName = Literal["inbound.message_received", "inbound_message_received"]


class InboundWebhookEvent(BaseModel):
    """A single event within an inbound webhook delivery.

    Mailtrap batches events, so one delivery can carry several. Each ``message_id`` is the inbound
    message object id (the same id used by ``GET /api/inbound/inboxes/{inbox_id}/messages/{id}``)
    — fetch the full body/attachments via the generated client rather than trusting this envelope.

    Tolerant of Mailtrap's panel "Send Test Webhook" sample, which uses a slightly different
    shape (``inbound_inbox_id`` instead of ``inbox_id``, no ``event_id``) than live deliveries.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    event: InboundWebhookEventName
    # Live deliveries carry a unique event_id; the panel test sample omits it.
    event_id: str | None = None
    # Epoch milliseconds (Mailtrap sends ms, not seconds).
    timestamp: int
    # Accept both the live field name and the panel-test sample's ``inbound_inbox_id``.
    inbox_id: int = Field(validation_alias=AliasChoices("inbox_id", "inbound_inbox_id"))
    message_id: str
    # RFC 5322 mailbox — may be "Name <addr>", not a bare email, so keep it as str.
    from_: str | None = Field(default=None, alias="from")

    @property
    def occurred_at(self) -> datetime:
        """Event time as an aware datetime (timestamp is epoch milliseconds)."""
        return datetime.fromtimestamp(self.timestamp / 1000, tz=UTC)


class InboundWebhookPayload(BaseModel):
    """Envelope wrapping the list of events Mailtrap posts to the webhook URL."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    events: list[InboundWebhookEvent] = Field(default_factory=list)
