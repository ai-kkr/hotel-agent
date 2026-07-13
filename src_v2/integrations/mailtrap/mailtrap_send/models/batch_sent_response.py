from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.batch_sent_response_responses_item import (
        BatchSentResponseResponsesItem,
    )


T = TypeVar("T", bound="BatchSentResponse")


@_attrs_define
class BatchSentResponse:
    """
    Attributes:
        success (bool | Unset): Overall request success Example: True.
        responses (list[BatchSentResponseResponsesItem] | Unset): Individual message results
        errors (list[str] | Unset): General errors
    """

    success: bool | Unset = UNSET
    responses: list[BatchSentResponseResponsesItem] | Unset = UNSET
    errors: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        success = self.success

        responses: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.responses, Unset):
            responses = []
            for responses_item_data in self.responses:
                responses_item = responses_item_data.to_dict()
                responses.append(responses_item)

        errors: list[str] | Unset = UNSET
        if not isinstance(self.errors, Unset):
            errors = self.errors

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if success is not UNSET:
            field_dict["success"] = success
        if responses is not UNSET:
            field_dict["responses"] = responses
        if errors is not UNSET:
            field_dict["errors"] = errors

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.batch_sent_response_responses_item import (
            BatchSentResponseResponsesItem,
        )

        d = dict(src_dict)
        success = d.pop("success", UNSET)

        _responses = d.pop("responses", UNSET)
        responses: list[BatchSentResponseResponsesItem] | Unset = UNSET
        if _responses is not UNSET:
            responses = []
            for responses_item_data in _responses:
                responses_item = BatchSentResponseResponsesItem.from_dict(
                    responses_item_data
                )

                responses.append(responses_item)

        errors = cast(list[str], d.pop("errors", UNSET))

        batch_sent_response = cls(
            success=success,
            responses=responses,
            errors=errors,
        )

        batch_sent_response.additional_properties = d
        return batch_sent_response

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
