from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DomainPermissions")


@_attrs_define
class DomainPermissions:
    """
    Attributes:
        can_read (bool | Unset):
        can_update (bool | Unset):
        can_destroy (bool | Unset):
    """

    can_read: bool | Unset = UNSET
    can_update: bool | Unset = UNSET
    can_destroy: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        can_read = self.can_read

        can_update = self.can_update

        can_destroy = self.can_destroy

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if can_read is not UNSET:
            field_dict["can_read"] = can_read
        if can_update is not UNSET:
            field_dict["can_update"] = can_update
        if can_destroy is not UNSET:
            field_dict["can_destroy"] = can_destroy

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        can_read = d.pop("can_read", UNSET)

        can_update = d.pop("can_update", UNSET)

        can_destroy = d.pop("can_destroy", UNSET)

        domain_permissions = cls(
            can_read=can_read,
            can_update=can_update,
            can_destroy=can_destroy,
        )

        domain_permissions.additional_properties = d
        return domain_permissions

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
