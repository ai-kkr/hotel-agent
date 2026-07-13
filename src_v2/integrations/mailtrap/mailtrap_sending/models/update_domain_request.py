from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="UpdateDomainRequest")


@_attrs_define
class UpdateDomainRequest:
    """
    Attributes:
        open_tracking_enabled (bool | Unset): Enable open tracking for emails sent from this domain
        click_tracking_enabled (bool | Unset): Enable click tracking for links in emails sent from this domain
        auto_unsubscribe_link_enabled (bool | Unset): Automatically add an unsubscribe link to emails sent from this
            domain
    """

    open_tracking_enabled: bool | Unset = UNSET
    click_tracking_enabled: bool | Unset = UNSET
    auto_unsubscribe_link_enabled: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        open_tracking_enabled = self.open_tracking_enabled

        click_tracking_enabled = self.click_tracking_enabled

        auto_unsubscribe_link_enabled = self.auto_unsubscribe_link_enabled

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if open_tracking_enabled is not UNSET:
            field_dict["open_tracking_enabled"] = open_tracking_enabled
        if click_tracking_enabled is not UNSET:
            field_dict["click_tracking_enabled"] = click_tracking_enabled
        if auto_unsubscribe_link_enabled is not UNSET:
            field_dict["auto_unsubscribe_link_enabled"] = auto_unsubscribe_link_enabled

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        open_tracking_enabled = d.pop("open_tracking_enabled", UNSET)

        click_tracking_enabled = d.pop("click_tracking_enabled", UNSET)

        auto_unsubscribe_link_enabled = d.pop("auto_unsubscribe_link_enabled", UNSET)

        update_domain_request = cls(
            open_tracking_enabled=open_tracking_enabled,
            click_tracking_enabled=click_tracking_enabled,
            auto_unsubscribe_link_enabled=auto_unsubscribe_link_enabled,
        )

        update_domain_request.additional_properties = d
        return update_domain_request

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
