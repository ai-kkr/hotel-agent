from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.create_webhook_body_webhook_event_types_item import (
    CreateWebhookBodyWebhookEventTypesItem,
)
from ..models.create_webhook_body_webhook_payload_format import (
    CreateWebhookBodyWebhookPayloadFormat,
)
from ..models.create_webhook_body_webhook_sending_stream import (
    CreateWebhookBodyWebhookSendingStream,
)
from ..models.create_webhook_body_webhook_webhook_type import (
    CreateWebhookBodyWebhookWebhookType,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="CreateWebhookBodyWebhook")


@_attrs_define
class CreateWebhookBodyWebhook:
    """
    Attributes:
        url (str): The URL that will receive webhook payloads. Example: https://example.com/mailtrap/webhooks.
        webhook_type (CreateWebhookBodyWebhookWebhookType): The type of webhook. Determines which events the webhook can
            subscribe to.
             Example: email_sending.
        active (bool | Unset): Whether the webhook is active. Defaults to `true`. Default: True. Example: True.
        payload_format (CreateWebhookBodyWebhookPayloadFormat | Unset): Format of the webhook payload. Default:
            CreateWebhookBodyWebhookPayloadFormat.JSON. Example: json.
        sending_stream (CreateWebhookBodyWebhookSendingStream | Unset): Sending stream the webhook subscribes to.
            Required for `email_sending` webhook type.
             Example: transactional.
        event_types (list[CreateWebhookBodyWebhookEventTypesItem] | Unset): List of event types to subscribe to.
            Required for `email_sending` and `campaigns` webhook types.
             Example: ['delivery', 'bounce'].
        domain_id (int | Unset): Scopes the webhook to a specific domain ID, or all
            domains if omitted. Applicable only for `email_sending`
            and `campaigns` webhooks.
             Example: 435.
        inbound_inbox_id (int | Unset): ID of the inbound inbox the webhook is linked to.
            Required for `inbound_receiving` webhooks; must not be
            set for any other webhook type.
             Example: 1.
    """

    url: str
    webhook_type: CreateWebhookBodyWebhookWebhookType
    active: bool | Unset = True
    payload_format: CreateWebhookBodyWebhookPayloadFormat | Unset = (
        CreateWebhookBodyWebhookPayloadFormat.JSON
    )
    sending_stream: CreateWebhookBodyWebhookSendingStream | Unset = UNSET
    event_types: list[CreateWebhookBodyWebhookEventTypesItem] | Unset = UNSET
    domain_id: int | Unset = UNSET
    inbound_inbox_id: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        url = self.url

        webhook_type = self.webhook_type.value

        active = self.active

        payload_format: str | Unset = UNSET
        if not isinstance(self.payload_format, Unset):
            payload_format = self.payload_format.value

        sending_stream: str | Unset = UNSET
        if not isinstance(self.sending_stream, Unset):
            sending_stream = self.sending_stream.value

        event_types: list[str] | Unset = UNSET
        if not isinstance(self.event_types, Unset):
            event_types = []
            for event_types_item_data in self.event_types:
                event_types_item = event_types_item_data.value
                event_types.append(event_types_item)

        domain_id = self.domain_id

        inbound_inbox_id = self.inbound_inbox_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "url": url,
                "webhook_type": webhook_type,
            }
        )
        if active is not UNSET:
            field_dict["active"] = active
        if payload_format is not UNSET:
            field_dict["payload_format"] = payload_format
        if sending_stream is not UNSET:
            field_dict["sending_stream"] = sending_stream
        if event_types is not UNSET:
            field_dict["event_types"] = event_types
        if domain_id is not UNSET:
            field_dict["domain_id"] = domain_id
        if inbound_inbox_id is not UNSET:
            field_dict["inbound_inbox_id"] = inbound_inbox_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        url = d.pop("url")

        webhook_type = CreateWebhookBodyWebhookWebhookType(d.pop("webhook_type"))

        active = d.pop("active", UNSET)

        _payload_format = d.pop("payload_format", UNSET)
        payload_format: CreateWebhookBodyWebhookPayloadFormat | Unset
        if isinstance(_payload_format, Unset):
            payload_format = UNSET
        else:
            payload_format = CreateWebhookBodyWebhookPayloadFormat(_payload_format)

        _sending_stream = d.pop("sending_stream", UNSET)
        sending_stream: CreateWebhookBodyWebhookSendingStream | Unset
        if isinstance(_sending_stream, Unset):
            sending_stream = UNSET
        else:
            sending_stream = CreateWebhookBodyWebhookSendingStream(_sending_stream)

        _event_types = d.pop("event_types", UNSET)
        event_types: list[CreateWebhookBodyWebhookEventTypesItem] | Unset = UNSET
        if _event_types is not UNSET:
            event_types = []
            for event_types_item_data in _event_types:
                event_types_item = CreateWebhookBodyWebhookEventTypesItem(
                    event_types_item_data
                )

                event_types.append(event_types_item)

        domain_id = d.pop("domain_id", UNSET)

        inbound_inbox_id = d.pop("inbound_inbox_id", UNSET)

        create_webhook_body_webhook = cls(
            url=url,
            webhook_type=webhook_type,
            active=active,
            payload_format=payload_format,
            sending_stream=sending_stream,
            event_types=event_types,
            domain_id=domain_id,
            inbound_inbox_id=inbound_inbox_id,
        )

        create_webhook_body_webhook.additional_properties = d
        return create_webhook_body_webhook

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
