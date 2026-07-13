from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.filter_contain_string_operator import FilterContainStringOperator

T = TypeVar("T", bound="FilterContainString")


@_attrs_define
class FilterContainString:
    """
    Attributes:
        operator (FilterContainStringOperator):
        value (str):
    """

    operator: FilterContainStringOperator
    value: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        operator = self.operator.value

        value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "operator": operator,
                "value": value,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        operator = FilterContainStringOperator(d.pop("operator"))

        value = d.pop("value")

        filter_contain_string = cls(
            operator=operator,
            value=value,
        )

        filter_contain_string.additional_properties = d
        return filter_contain_string

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
