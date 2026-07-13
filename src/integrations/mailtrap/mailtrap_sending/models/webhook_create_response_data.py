from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.webhook_event_types_item import WebhookEventTypesItem
from ..models.webhook_payload_format import WebhookPayloadFormat
from ..models.webhook_sending_stream_type_1 import WebhookSendingStreamType1
from ..models.webhook_sending_stream_type_2_type_1 import WebhookSendingStreamType2Type1
from ..models.webhook_sending_stream_type_3_type_1 import WebhookSendingStreamType3Type1
from ..models.webhook_webhook_type import WebhookWebhookType
from ..types import UNSET, Unset

T = TypeVar("T", bound="WebhookCreateResponseData")


@_attrs_define
class WebhookCreateResponseData:
    """
    Attributes:
        id (int | Unset):  Example: 1.
        url (str | Unset):  Example: https://example.com/mailtrap/webhooks.
        active (bool | Unset):  Example: True.
        webhook_type (WebhookWebhookType | Unset):  Example: email_sending.
        payload_format (WebhookPayloadFormat | Unset):  Example: json.
        sending_stream (None | Unset | WebhookSendingStreamType1 | WebhookSendingStreamType2Type1 |
            WebhookSendingStreamType3Type1): Sending stream the webhook is subscribed to. Applicable only for
            `email_sending` webhooks.
             Example: transactional.
        domain_id (int | None | Unset): Scopes the webhook to a specific domain ID, or all domains if
            omitted. Applicable only for `email_sending` and `campaigns`
            webhooks.
             Example: 435.
        inbound_inbox_id (int | None | Unset): ID of the inbound inbox the webhook is linked to. Applicable only
            for `inbound_receiving` webhooks.
             Example: 1.
        event_types (list[WebhookEventTypesItem] | Unset): List of event types the webhook is subscribed to. Applicable
            only
            for `email_sending` and `campaigns` webhooks.
             Example: ['delivery', 'bounce'].
        signing_secret (str | Unset): Secret key for verifying webhook payload signatures using HMAC SHA-256. Only
            returned on creation.
             Example: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6.
    """

    id: int | Unset = UNSET
    url: str | Unset = UNSET
    active: bool | Unset = UNSET
    webhook_type: WebhookWebhookType | Unset = UNSET
    payload_format: WebhookPayloadFormat | Unset = UNSET
    sending_stream: (
        None
        | Unset
        | WebhookSendingStreamType1
        | WebhookSendingStreamType2Type1
        | WebhookSendingStreamType3Type1
    ) = UNSET
    domain_id: int | None | Unset = UNSET
    inbound_inbox_id: int | None | Unset = UNSET
    event_types: list[WebhookEventTypesItem] | Unset = UNSET
    signing_secret: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        url = self.url

        active = self.active

        webhook_type: str | Unset = UNSET
        if not isinstance(self.webhook_type, Unset):
            webhook_type = self.webhook_type.value

        payload_format: str | Unset = UNSET
        if not isinstance(self.payload_format, Unset):
            payload_format = self.payload_format.value

        sending_stream: None | str | Unset
        if isinstance(self.sending_stream, Unset):
            sending_stream = UNSET
        elif isinstance(self.sending_stream, WebhookSendingStreamType1) or isinstance(self.sending_stream, WebhookSendingStreamType2Type1) or isinstance(self.sending_stream, WebhookSendingStreamType3Type1):
            sending_stream = self.sending_stream.value
        else:
            sending_stream = self.sending_stream

        domain_id: int | None | Unset
        if isinstance(self.domain_id, Unset):
            domain_id = UNSET
        else:
            domain_id = self.domain_id

        inbound_inbox_id: int | None | Unset
        if isinstance(self.inbound_inbox_id, Unset):
            inbound_inbox_id = UNSET
        else:
            inbound_inbox_id = self.inbound_inbox_id

        event_types: list[str] | Unset = UNSET
        if not isinstance(self.event_types, Unset):
            event_types = []
            for event_types_item_data in self.event_types:
                event_types_item = event_types_item_data.value
                event_types.append(event_types_item)

        signing_secret = self.signing_secret

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if url is not UNSET:
            field_dict["url"] = url
        if active is not UNSET:
            field_dict["active"] = active
        if webhook_type is not UNSET:
            field_dict["webhook_type"] = webhook_type
        if payload_format is not UNSET:
            field_dict["payload_format"] = payload_format
        if sending_stream is not UNSET:
            field_dict["sending_stream"] = sending_stream
        if domain_id is not UNSET:
            field_dict["domain_id"] = domain_id
        if inbound_inbox_id is not UNSET:
            field_dict["inbound_inbox_id"] = inbound_inbox_id
        if event_types is not UNSET:
            field_dict["event_types"] = event_types
        if signing_secret is not UNSET:
            field_dict["signing_secret"] = signing_secret

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        url = d.pop("url", UNSET)

        active = d.pop("active", UNSET)

        _webhook_type = d.pop("webhook_type", UNSET)
        webhook_type: WebhookWebhookType | Unset
        if isinstance(_webhook_type, Unset):
            webhook_type = UNSET
        else:
            webhook_type = WebhookWebhookType(_webhook_type)

        _payload_format = d.pop("payload_format", UNSET)
        payload_format: WebhookPayloadFormat | Unset
        if isinstance(_payload_format, Unset):
            payload_format = UNSET
        else:
            payload_format = WebhookPayloadFormat(_payload_format)

        def _parse_sending_stream(
            data: object,
        ) -> (
            None
            | Unset
            | WebhookSendingStreamType1
            | WebhookSendingStreamType2Type1
            | WebhookSendingStreamType3Type1
        ):
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                sending_stream_type_1 = WebhookSendingStreamType1(data)

                return sending_stream_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, str):
                    raise TypeError()
                sending_stream_type_2_type_1 = WebhookSendingStreamType2Type1(data)

                return sending_stream_type_2_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, str):
                    raise TypeError()
                sending_stream_type_3_type_1 = WebhookSendingStreamType3Type1(data)

                return sending_stream_type_3_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(
                None
                | Unset
                | WebhookSendingStreamType1
                | WebhookSendingStreamType2Type1
                | WebhookSendingStreamType3Type1,
                data,
            )

        sending_stream = _parse_sending_stream(d.pop("sending_stream", UNSET))

        def _parse_domain_id(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        domain_id = _parse_domain_id(d.pop("domain_id", UNSET))

        def _parse_inbound_inbox_id(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        inbound_inbox_id = _parse_inbound_inbox_id(d.pop("inbound_inbox_id", UNSET))

        _event_types = d.pop("event_types", UNSET)
        event_types: list[WebhookEventTypesItem] | Unset = UNSET
        if _event_types is not UNSET:
            event_types = []
            for event_types_item_data in _event_types:
                event_types_item = WebhookEventTypesItem(event_types_item_data)

                event_types.append(event_types_item)

        signing_secret = d.pop("signing_secret", UNSET)

        webhook_create_response_data = cls(
            id=id,
            url=url,
            active=active,
            webhook_type=webhook_type,
            payload_format=payload_format,
            sending_stream=sending_stream,
            domain_id=domain_id,
            inbound_inbox_id=inbound_inbox_id,
            event_types=event_types,
            signing_secret=signing_secret,
        )

        webhook_create_response_data.additional_properties = d
        return webhook_create_response_data

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
