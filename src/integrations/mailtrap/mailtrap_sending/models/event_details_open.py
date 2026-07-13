from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="EventDetailsOpen")


@_attrs_define
class EventDetailsOpen:
    """For event_type = open

    Example:
        {'web_ip_address': '198.51.100.50'}

    Attributes:
        web_ip_address (None | str | Unset):
    """

    web_ip_address: None | str | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        web_ip_address: None | str | Unset
        if isinstance(self.web_ip_address, Unset):
            web_ip_address = UNSET
        else:
            web_ip_address = self.web_ip_address

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if web_ip_address is not UNSET:
            field_dict["web_ip_address"] = web_ip_address

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_web_ip_address(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        web_ip_address = _parse_web_ip_address(d.pop("web_ip_address", UNSET))

        event_details_open = cls(
            web_ip_address=web_ip_address,
        )

        return event_details_open
