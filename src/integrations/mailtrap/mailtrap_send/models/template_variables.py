from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.template_variables_template_variables import (
        TemplateVariablesTemplateVariables,
    )


T = TypeVar("T", bound="TemplateVariables")


@_attrs_define
class TemplateVariables:
    """
    Attributes:
        template_variables (TemplateVariablesTemplateVariables | Unset): Template variable values Example: {'user_name':
            'John Doe', 'order_number': '12345'}.
    """

    template_variables: TemplateVariablesTemplateVariables | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        template_variables: dict[str, Any] | Unset = UNSET
        if not isinstance(self.template_variables, Unset):
            template_variables = self.template_variables.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if template_variables is not UNSET:
            field_dict["template_variables"] = template_variables

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.template_variables_template_variables import (
            TemplateVariablesTemplateVariables,
        )

        d = dict(src_dict)
        _template_variables = d.pop("template_variables", UNSET)
        template_variables: TemplateVariablesTemplateVariables | Unset
        if isinstance(_template_variables, Unset):
            template_variables = UNSET
        else:
            template_variables = TemplateVariablesTemplateVariables.from_dict(
                _template_variables
            )

        template_variables = cls(
            template_variables=template_variables,
        )

        template_variables.additional_properties = d
        return template_variables

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
