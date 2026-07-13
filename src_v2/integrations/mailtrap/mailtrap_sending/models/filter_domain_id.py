from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.filter_domain_id_operator import FilterDomainIdOperator

T = TypeVar("T", bound="FilterDomainId")


@_attrs_define
class FilterDomainId:
    """
    Example:
        {'operator': 'equal', 'value': 3938}

    Attributes:
        operator (FilterDomainIdOperator):
        value (int | list[int]):
    """

    operator: FilterDomainIdOperator
    value: int | list[int]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        operator = self.operator.value

        value: int | list[int]
        if isinstance(self.value, list):
            value = self.value

        else:
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
        operator = FilterDomainIdOperator(d.pop("operator"))

        def _parse_value(data: object) -> int | list[int]:
            try:
                if not isinstance(data, list):
                    raise TypeError()
                value_type_1 = cast(list[int], data)

                return value_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(int | list[int], data)

        value = _parse_value(d.pop("value"))

        filter_domain_id = cls(
            operator=operator,
            value=value,
        )

        filter_domain_id.additional_properties = d
        return filter_domain_id

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
