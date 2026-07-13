from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="BatchSentResponseResponsesItem")


@_attrs_define
class BatchSentResponseResponsesItem:
    """
    Attributes:
        success (bool | Unset):  Example: True.
        message_ids (list[str] | Unset):
        errors (list[str] | Unset):
    """

    success: bool | Unset = UNSET
    message_ids: list[str] | Unset = UNSET
    errors: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        success = self.success

        message_ids: list[str] | Unset = UNSET
        if not isinstance(self.message_ids, Unset):
            message_ids = self.message_ids

        errors: list[str] | Unset = UNSET
        if not isinstance(self.errors, Unset):
            errors = self.errors

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if success is not UNSET:
            field_dict["success"] = success
        if message_ids is not UNSET:
            field_dict["message_ids"] = message_ids
        if errors is not UNSET:
            field_dict["errors"] = errors

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        success = d.pop("success", UNSET)

        message_ids = cast(list[str], d.pop("message_ids", UNSET))

        errors = cast(list[str], d.pop("errors", UNSET))

        batch_sent_response_responses_item = cls(
            success=success,
            message_ids=message_ids,
            errors=errors,
        )

        batch_sent_response_responses_item.additional_properties = d
        return batch_sent_response_responses_item

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
