from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.update_webhook_body_webhook_event_types_item import (
    UpdateWebhookBodyWebhookEventTypesItem,
)
from ..models.update_webhook_body_webhook_payload_format import (
    UpdateWebhookBodyWebhookPayloadFormat,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="UpdateWebhookBodyWebhook")


@_attrs_define
class UpdateWebhookBodyWebhook:
    """
    Attributes:
        url (str | Unset): The URL that will receive webhook payloads. Example: https://example.com/mailtrap/webhooks.
        active (bool | Unset): Whether the webhook is active.
        payload_format (UpdateWebhookBodyWebhookPayloadFormat | Unset): Format of the webhook payload. Example: json.
        event_types (list[UpdateWebhookBodyWebhookEventTypesItem] | Unset): List of event types to subscribe to.
            Applicable only for `email_sending` and `campaigns` webhooks. Example: ['delivery', 'bounce', 'unsubscribe'].
        inbound_inbox_id (int | Unset): ID of the inbound inbox the webhook is linked to.
            Applicable only for `inbound_receiving` webhooks.
             Example: 1.
    """

    url: str | Unset = UNSET
    active: bool | Unset = UNSET
    payload_format: UpdateWebhookBodyWebhookPayloadFormat | Unset = UNSET
    event_types: list[UpdateWebhookBodyWebhookEventTypesItem] | Unset = UNSET
    inbound_inbox_id: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        url = self.url

        active = self.active

        payload_format: str | Unset = UNSET
        if not isinstance(self.payload_format, Unset):
            payload_format = self.payload_format.value

        event_types: list[str] | Unset = UNSET
        if not isinstance(self.event_types, Unset):
            event_types = []
            for event_types_item_data in self.event_types:
                event_types_item = event_types_item_data.value
                event_types.append(event_types_item)

        inbound_inbox_id = self.inbound_inbox_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if url is not UNSET:
            field_dict["url"] = url
        if active is not UNSET:
            field_dict["active"] = active
        if payload_format is not UNSET:
            field_dict["payload_format"] = payload_format
        if event_types is not UNSET:
            field_dict["event_types"] = event_types
        if inbound_inbox_id is not UNSET:
            field_dict["inbound_inbox_id"] = inbound_inbox_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        url = d.pop("url", UNSET)

        active = d.pop("active", UNSET)

        _payload_format = d.pop("payload_format", UNSET)
        payload_format: UpdateWebhookBodyWebhookPayloadFormat | Unset
        if isinstance(_payload_format, Unset):
            payload_format = UNSET
        else:
            payload_format = UpdateWebhookBodyWebhookPayloadFormat(_payload_format)

        _event_types = d.pop("event_types", UNSET)
        event_types: list[UpdateWebhookBodyWebhookEventTypesItem] | Unset = UNSET
        if _event_types is not UNSET:
            event_types = []
            for event_types_item_data in _event_types:
                event_types_item = UpdateWebhookBodyWebhookEventTypesItem(
                    event_types_item_data
                )

                event_types.append(event_types_item)

        inbound_inbox_id = d.pop("inbound_inbox_id", UNSET)

        update_webhook_body_webhook = cls(
            url=url,
            active=active,
            payload_format=payload_format,
            event_types=event_types,
            inbound_inbox_id=inbound_inbox_id,
        )

        update_webhook_body_webhook.additional_properties = d
        return update_webhook_body_webhook

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
