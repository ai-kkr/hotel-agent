from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.suppression_sending_stream import SuppressionSendingStream
from ..models.suppression_type import SuppressionType
from ..types import UNSET, Unset

T = TypeVar("T", bound="Suppression")


@_attrs_define
class Suppression:
    """
    Attributes:
        id (UUID | Unset): The suppression UUID Example: 64d71bf3-1276-417b-86e1-8e66f138acfe.
        type_ (SuppressionType | Unset): Reason for the suppression Example: hard bounce.
        created_at (datetime.datetime | Unset):  Example: 2025-01-15T10:30:00Z.
        email (str | Unset):  Example: suppressed@example.com.
        sending_stream (SuppressionSendingStream | Unset):  Example: transactional.
        domain_name (None | str | Unset):  Example: example.com.
        message_bounce_category (None | str | Unset):
        message_category (None | str | Unset):
        message_client_ip (None | str | Unset):
        message_created_at (datetime.datetime | None | Unset):
        message_esp_response (None | str | Unset):
        message_esp_server_type (None | str | Unset):
        message_outgoing_ip (None | str | Unset):
        message_recipient_mx_name (None | str | Unset):
        message_sender_email (None | str | Unset):
        message_subject (None | str | Unset):
    """

    id: UUID | Unset = UNSET
    type_: SuppressionType | Unset = UNSET
    created_at: datetime.datetime | Unset = UNSET
    email: str | Unset = UNSET
    sending_stream: SuppressionSendingStream | Unset = UNSET
    domain_name: None | str | Unset = UNSET
    message_bounce_category: None | str | Unset = UNSET
    message_category: None | str | Unset = UNSET
    message_client_ip: None | str | Unset = UNSET
    message_created_at: datetime.datetime | None | Unset = UNSET
    message_esp_response: None | str | Unset = UNSET
    message_esp_server_type: None | str | Unset = UNSET
    message_outgoing_ip: None | str | Unset = UNSET
    message_recipient_mx_name: None | str | Unset = UNSET
    message_sender_email: None | str | Unset = UNSET
    message_subject: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        type_: str | Unset = UNSET
        if not isinstance(self.type_, Unset):
            type_ = self.type_.value

        created_at: str | Unset = UNSET
        if not isinstance(self.created_at, Unset):
            created_at = self.created_at.isoformat()

        email = self.email

        sending_stream: str | Unset = UNSET
        if not isinstance(self.sending_stream, Unset):
            sending_stream = self.sending_stream.value

        domain_name: None | str | Unset
        if isinstance(self.domain_name, Unset):
            domain_name = UNSET
        else:
            domain_name = self.domain_name

        message_bounce_category: None | str | Unset
        if isinstance(self.message_bounce_category, Unset):
            message_bounce_category = UNSET
        else:
            message_bounce_category = self.message_bounce_category

        message_category: None | str | Unset
        if isinstance(self.message_category, Unset):
            message_category = UNSET
        else:
            message_category = self.message_category

        message_client_ip: None | str | Unset
        if isinstance(self.message_client_ip, Unset):
            message_client_ip = UNSET
        else:
            message_client_ip = self.message_client_ip

        message_created_at: None | str | Unset
        if isinstance(self.message_created_at, Unset):
            message_created_at = UNSET
        elif isinstance(self.message_created_at, datetime.datetime):
            message_created_at = self.message_created_at.isoformat()
        else:
            message_created_at = self.message_created_at

        message_esp_response: None | str | Unset
        if isinstance(self.message_esp_response, Unset):
            message_esp_response = UNSET
        else:
            message_esp_response = self.message_esp_response

        message_esp_server_type: None | str | Unset
        if isinstance(self.message_esp_server_type, Unset):
            message_esp_server_type = UNSET
        else:
            message_esp_server_type = self.message_esp_server_type

        message_outgoing_ip: None | str | Unset
        if isinstance(self.message_outgoing_ip, Unset):
            message_outgoing_ip = UNSET
        else:
            message_outgoing_ip = self.message_outgoing_ip

        message_recipient_mx_name: None | str | Unset
        if isinstance(self.message_recipient_mx_name, Unset):
            message_recipient_mx_name = UNSET
        else:
            message_recipient_mx_name = self.message_recipient_mx_name

        message_sender_email: None | str | Unset
        if isinstance(self.message_sender_email, Unset):
            message_sender_email = UNSET
        else:
            message_sender_email = self.message_sender_email

        message_subject: None | str | Unset
        if isinstance(self.message_subject, Unset):
            message_subject = UNSET
        else:
            message_subject = self.message_subject

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if type_ is not UNSET:
            field_dict["type"] = type_
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if email is not UNSET:
            field_dict["email"] = email
        if sending_stream is not UNSET:
            field_dict["sending_stream"] = sending_stream
        if domain_name is not UNSET:
            field_dict["domain_name"] = domain_name
        if message_bounce_category is not UNSET:
            field_dict["message_bounce_category"] = message_bounce_category
        if message_category is not UNSET:
            field_dict["message_category"] = message_category
        if message_client_ip is not UNSET:
            field_dict["message_client_ip"] = message_client_ip
        if message_created_at is not UNSET:
            field_dict["message_created_at"] = message_created_at
        if message_esp_response is not UNSET:
            field_dict["message_esp_response"] = message_esp_response
        if message_esp_server_type is not UNSET:
            field_dict["message_esp_server_type"] = message_esp_server_type
        if message_outgoing_ip is not UNSET:
            field_dict["message_outgoing_ip"] = message_outgoing_ip
        if message_recipient_mx_name is not UNSET:
            field_dict["message_recipient_mx_name"] = message_recipient_mx_name
        if message_sender_email is not UNSET:
            field_dict["message_sender_email"] = message_sender_email
        if message_subject is not UNSET:
            field_dict["message_subject"] = message_subject

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _id = d.pop("id", UNSET)
        id: UUID | Unset
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        _type_ = d.pop("type", UNSET)
        type_: SuppressionType | Unset
        if isinstance(_type_, Unset):
            type_ = UNSET
        else:
            type_ = SuppressionType(_type_)

        _created_at = d.pop("created_at", UNSET)
        created_at: datetime.datetime | Unset
        if isinstance(_created_at, Unset):
            created_at = UNSET
        else:
            created_at = datetime.datetime.fromisoformat(_created_at)

        email = d.pop("email", UNSET)

        _sending_stream = d.pop("sending_stream", UNSET)
        sending_stream: SuppressionSendingStream | Unset
        if isinstance(_sending_stream, Unset):
            sending_stream = UNSET
        else:
            sending_stream = SuppressionSendingStream(_sending_stream)

        def _parse_domain_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        domain_name = _parse_domain_name(d.pop("domain_name", UNSET))

        def _parse_message_bounce_category(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message_bounce_category = _parse_message_bounce_category(
            d.pop("message_bounce_category", UNSET)
        )

        def _parse_message_category(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message_category = _parse_message_category(d.pop("message_category", UNSET))

        def _parse_message_client_ip(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message_client_ip = _parse_message_client_ip(d.pop("message_client_ip", UNSET))

        def _parse_message_created_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                message_created_at_type_0 = datetime.datetime.fromisoformat(data)

                return message_created_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        message_created_at = _parse_message_created_at(
            d.pop("message_created_at", UNSET)
        )

        def _parse_message_esp_response(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message_esp_response = _parse_message_esp_response(
            d.pop("message_esp_response", UNSET)
        )

        def _parse_message_esp_server_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message_esp_server_type = _parse_message_esp_server_type(
            d.pop("message_esp_server_type", UNSET)
        )

        def _parse_message_outgoing_ip(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message_outgoing_ip = _parse_message_outgoing_ip(
            d.pop("message_outgoing_ip", UNSET)
        )

        def _parse_message_recipient_mx_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message_recipient_mx_name = _parse_message_recipient_mx_name(
            d.pop("message_recipient_mx_name", UNSET)
        )

        def _parse_message_sender_email(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message_sender_email = _parse_message_sender_email(
            d.pop("message_sender_email", UNSET)
        )

        def _parse_message_subject(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message_subject = _parse_message_subject(d.pop("message_subject", UNSET))

        suppression = cls(
            id=id,
            type_=type_,
            created_at=created_at,
            email=email,
            sending_stream=sending_stream,
            domain_name=domain_name,
            message_bounce_category=message_bounce_category,
            message_category=message_category,
            message_client_ip=message_client_ip,
            message_created_at=message_created_at,
            message_esp_response=message_esp_response,
            message_esp_server_type=message_esp_server_type,
            message_outgoing_ip=message_outgoing_ip,
            message_recipient_mx_name=message_recipient_mx_name,
            message_sender_email=message_sender_email,
            message_subject=message_subject,
        )

        suppression.additional_properties = d
        return suppression

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
