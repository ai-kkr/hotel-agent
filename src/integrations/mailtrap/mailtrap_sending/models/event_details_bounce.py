from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="EventDetailsBounce")


@_attrs_define
class EventDetailsBounce:
    """For event_type = soft_bounce or bounce

    Example:
        {'sending_ip': '192.0.2.1', 'recipient_mx': 'mx.example.com', 'email_service_provider': 'Google',
            'email_service_provider_status': '5.7.1', 'email_service_provider_response': 'User unknown', 'bounce_category':
            'invalid_recipient'}

    Attributes:
        sending_ip (None | str | Unset):
        recipient_mx (None | str | Unset):
        email_service_provider (None | str | Unset):
        email_service_provider_status (None | str | Unset):
        email_service_provider_response (None | str | Unset):
        bounce_category (None | str | Unset):
    """

    sending_ip: None | str | Unset = UNSET
    recipient_mx: None | str | Unset = UNSET
    email_service_provider: None | str | Unset = UNSET
    email_service_provider_status: None | str | Unset = UNSET
    email_service_provider_response: None | str | Unset = UNSET
    bounce_category: None | str | Unset = UNSET

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

        email_service_provider_status: None | str | Unset
        if isinstance(self.email_service_provider_status, Unset):
            email_service_provider_status = UNSET
        else:
            email_service_provider_status = self.email_service_provider_status

        email_service_provider_response: None | str | Unset
        if isinstance(self.email_service_provider_response, Unset):
            email_service_provider_response = UNSET
        else:
            email_service_provider_response = self.email_service_provider_response

        bounce_category: None | str | Unset
        if isinstance(self.bounce_category, Unset):
            bounce_category = UNSET
        else:
            bounce_category = self.bounce_category

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if sending_ip is not UNSET:
            field_dict["sending_ip"] = sending_ip
        if recipient_mx is not UNSET:
            field_dict["recipient_mx"] = recipient_mx
        if email_service_provider is not UNSET:
            field_dict["email_service_provider"] = email_service_provider
        if email_service_provider_status is not UNSET:
            field_dict["email_service_provider_status"] = email_service_provider_status
        if email_service_provider_response is not UNSET:
            field_dict["email_service_provider_response"] = (
                email_service_provider_response
            )
        if bounce_category is not UNSET:
            field_dict["bounce_category"] = bounce_category

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

        def _parse_email_service_provider_status(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        email_service_provider_status = _parse_email_service_provider_status(
            d.pop("email_service_provider_status", UNSET)
        )

        def _parse_email_service_provider_response(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        email_service_provider_response = _parse_email_service_provider_response(
            d.pop("email_service_provider_response", UNSET)
        )

        def _parse_bounce_category(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        bounce_category = _parse_bounce_category(d.pop("bounce_category", UNSET))

        event_details_bounce = cls(
            sending_ip=sending_ip,
            recipient_mx=recipient_mx,
            email_service_provider=email_service_provider,
            email_service_provider_status=email_service_provider_status,
            email_service_provider_response=email_service_provider_response,
            bounce_category=bounce_category,
        )

        return event_details_bounce
