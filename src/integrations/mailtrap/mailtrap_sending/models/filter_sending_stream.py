from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.filter_sending_stream_operator import FilterSendingStreamOperator
from ..models.filter_sending_stream_value_type_0 import FilterSendingStreamValueType0
from ..models.filter_sending_stream_value_type_1_item import (
    FilterSendingStreamValueType1Item,
)

T = TypeVar("T", bound="FilterSendingStream")


@_attrs_define
class FilterSendingStream:
    """
    Example:
        {'operator': 'equal', 'value': 'transactional'}

    Attributes:
        operator (FilterSendingStreamOperator):
        value (FilterSendingStreamValueType0 | list[FilterSendingStreamValueType1Item]):
    """

    operator: FilterSendingStreamOperator
    value: FilterSendingStreamValueType0 | list[FilterSendingStreamValueType1Item]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        operator = self.operator.value

        value: list[str] | str
        if isinstance(self.value, FilterSendingStreamValueType0):
            value = self.value.value
        else:
            value = []
            for value_type_1_item_data in self.value:
                value_type_1_item = value_type_1_item_data.value
                value.append(value_type_1_item)

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
        operator = FilterSendingStreamOperator(d.pop("operator"))

        def _parse_value(
            data: object,
        ) -> FilterSendingStreamValueType0 | list[FilterSendingStreamValueType1Item]:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                value_type_0 = FilterSendingStreamValueType0(data)

                return value_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, list):
                raise TypeError()
            value_type_1 = []
            _value_type_1 = data
            for value_type_1_item_data in _value_type_1:
                value_type_1_item = FilterSendingStreamValueType1Item(
                    value_type_1_item_data
                )

                value_type_1.append(value_type_1_item)

            return value_type_1

        value = _parse_value(d.pop("value"))

        filter_sending_stream = cls(
            operator=operator,
            value=value,
        )

        filter_sending_stream.additional_properties = d
        return filter_sending_stream

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
