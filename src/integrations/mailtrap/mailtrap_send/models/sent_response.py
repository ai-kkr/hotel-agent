from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SentResponse")


@_attrs_define
class SentResponse:
    """
    Attributes:
        success (bool | Unset):  Example: True.
        message_ids (list[str] | Unset): Message IDs (one per recipient)
    """

    success: bool | Unset = UNSET
    message_ids: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        success = self.success

        message_ids: list[str] | Unset = UNSET
        if not isinstance(self.message_ids, Unset):
            message_ids = self.message_ids

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if success is not UNSET:
            field_dict["success"] = success
        if message_ids is not UNSET:
            field_dict["message_ids"] = message_ids

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        success = d.pop("success", UNSET)

        message_ids = cast(list[str], d.pop("message_ids", UNSET))

        sent_response = cls(
            success=success,
            message_ids=message_ids,
        )

        sent_response.additional_properties = d
        return sent_response

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
