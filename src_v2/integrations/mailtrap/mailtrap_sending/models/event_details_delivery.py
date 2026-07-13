from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="EventDetailsDelivery")


@_attrs_define
class EventDetailsDelivery:
    """For event_type = delivery

    Example:
        {'sending_ip': '192.0.2.1', 'recipient_mx': 'gmail-smtp-in.l.google.com', 'email_service_provider': 'Google'}

    Attributes:
        sending_ip (None | str | Unset):
        recipient_mx (None | str | Unset):
        email_service_provider (None | str | Unset):
    """

    sending_ip: None | str | Unset = UNSET
    recipient_mx: None | str | Unset = UNSET
    email_service_provider: None | str | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        sending_ip: None | str | Unset
        if isinstance(self.sending_ip, Unset):
            sending_ip = UNSET
        else:
            sending_ip = self.sending_ip

        recipient_mx: None | str | Unset
        if isinstance(self.recipient_mx, Unset):
            recipient_mx = UNSET
        else:
            recipient_mx = self.recipient_mx

        email_service_provider: None | str | Unset
        if isinstance(self.email_service_provider, Unset):
            email_service_provider = UNSET
        else:
            email_service_provider = self.email_service_provider

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if sending_ip is not UNSET:
            field_dict["sending_ip"] = sending_ip
        if recipient_mx is not UNSET:
            field_dict["recipient_mx"] = recipient_mx
        if email_service_provider is not UNSET:
            field_dict["email_service_provider"] = email_service_provider

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_sending_ip(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        sending_ip = _parse_sending_ip(d.pop("sending_ip", UNSET))

        def _parse_recipient_mx(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        recipient_mx = _parse_recipient_mx(d.pop("recipient_mx", UNSET))

        def _parse_email_service_provider(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        email_service_provider = _parse_email_service_provider(
            d.pop("email_service_provider", UNSET)
        )

        event_details_delivery = cls(
            sending_ip=sending_ip,
            recipient_mx=recipient_mx,
            email_service_provider=email_service_provider,
        )

        return event_details_delivery
