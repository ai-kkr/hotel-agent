from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.filter_email_service_provider_operator import (
    FilterEmailServiceProviderOperator,
)

T = TypeVar("T", bound="FilterEmailServiceProvider")


@_attrs_define
class FilterEmailServiceProvider:
    """
    Example:
        {'operator': 'equal', 'value': 'Google'}

    Attributes:
        operator (FilterEmailServiceProviderOperator):
        value (list[str] | str):
    """

    operator: FilterEmailServiceProviderOperator
    value: list[str] | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        operator = self.operator.value

        value: list[str] | str
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
        operator = FilterEmailServiceProviderOperator(d.pop("operator"))

        def _parse_value(data: object) -> list[str] | str:
            try:
                if not isinstance(data, list):
                    raise TypeError()
                value_type_1 = cast(list[str], data)

                return value_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | str, data)

        value = _parse_value(d.pop("value"))

        filter_email_service_provider = cls(
            operator=operator,
            value=value,
        )

        filter_email_service_provider.additional_properties = d
        return filter_email_service_provider

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
