from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.email_custom_variables_custom_variables import (
        EmailCustomVariablesCustomVariables,
    )


T = TypeVar("T", bound="EmailCustomVariables")


@_attrs_define
class EmailCustomVariables:
    """
    Attributes:
        custom_variables (EmailCustomVariablesCustomVariables | Unset):  Example: {'user_id': '12345', 'order_id':
            'ORD-789'}.
    """

    custom_variables: EmailCustomVariablesCustomVariables | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        custom_variables: dict[str, Any] | Unset = UNSET
        if not isinstance(self.custom_variables, Unset):
            custom_variables = self.custom_variables.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if custom_variables is not UNSET:
            field_dict["custom_variables"] = custom_variables

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.email_custom_variables_custom_variables import (
            EmailCustomVariablesCustomVariables,
        )

        d = dict(src_dict)
        _custom_variables = d.pop("custom_variables", UNSET)
        custom_variables: EmailCustomVariablesCustomVariables | Unset
        if isinstance(_custom_variables, Unset):
            custom_variables = UNSET
        else:
            custom_variables = EmailCustomVariablesCustomVariables.from_dict(
                _custom_variables
            )

        email_custom_variables = cls(
            custom_variables=custom_variables,
        )

        email_custom_variables.additional_properties = d
        return email_custom_variables

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
