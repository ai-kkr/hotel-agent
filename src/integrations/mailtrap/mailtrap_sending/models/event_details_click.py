from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="EventDetailsClick")


@_attrs_define
class EventDetailsClick:
    """For event_type = click

    Example:
        {'click_url': 'https://example.com/track/click/abc123', 'web_ip_address': '198.51.100.50'}

    Attributes:
        click_url (None | str | Unset):
        web_ip_address (None | str | Unset):
    """

    click_url: None | str | Unset = UNSET
    web_ip_address: None | str | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        click_url: None | str | Unset
        if isinstance(self.click_url, Unset):
            click_url = UNSET
        else:
            click_url = self.click_url

        web_ip_address: None | str | Unset
        if isinstance(self.web_ip_address, Unset):
            web_ip_address = UNSET
        else:
            web_ip_address = self.web_ip_address

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if click_url is not UNSET:
            field_dict["click_url"] = click_url
        if web_ip_address is not UNSET:
            field_dict["web_ip_address"] = web_ip_address

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_click_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        click_url = _parse_click_url(d.pop("click_url", UNSET))

        def _parse_web_ip_address(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        web_ip_address = _parse_web_ip_address(d.pop("web_ip_address", UNSET))

        event_details_click = cls(
            click_url=click_url,
            web_ip_address=web_ip_address,
        )

        return event_details_click
