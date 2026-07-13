from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.filter_events_operator import FilterEventsOperator
from ..models.filter_events_value_type_0 import FilterEventsValueType0
from ..models.filter_events_value_type_1_item import FilterEventsValueType1Item

T = TypeVar("T", bound="FilterEvents")


@_attrs_define
class FilterEvents:
    """
    Attributes:
        operator (FilterEventsOperator):
        value (FilterEventsValueType0 | list[FilterEventsValueType1Item]):
    """

    operator: FilterEventsOperator
    value: FilterEventsValueType0 | list[FilterEventsValueType1Item]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        operator = self.operator.value

        value: list[str] | str
        if isinstance(self.value, FilterEventsValueType0):
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
        operator = FilterEventsOperator(d.pop("operator"))

        def _parse_value(
            data: object,
        ) -> FilterEventsValueType0 | list[FilterEventsValueType1Item]:
            try:
                if not isinstance(data, str):
                    raise TypeError()
                value_type_0 = FilterEventsValueType0(data)

                return value_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, list):
                raise TypeError()
            value_type_1 = []
            _value_type_1 = data
            for value_type_1_item_data in _value_type_1:
                value_type_1_item = FilterEventsValueType1Item(value_type_1_item_data)

                value_type_1.append(value_type_1_item)

            return value_type_1

        value = _parse_value(d.pop("value"))

        filter_events = cls(
            operator=operator,
            value=value,
        )

        filter_events.additional_properties = d
        return filter_events

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
