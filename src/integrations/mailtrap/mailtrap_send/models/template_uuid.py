from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="TemplateUuid")


@_attrs_define
class TemplateUuid:
    """
    Attributes:
        template_uuid (UUID | Unset): Email template UUID Example: b81aabcd-1a1e-41cf-91b6-eca0254b3d96.
    """

    template_uuid: UUID | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        template_uuid: str | Unset = UNSET
        if not isinstance(self.template_uuid, Unset):
            template_uuid = str(self.template_uuid)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if template_uuid is not UNSET:
            field_dict["template_uuid"] = template_uuid

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _template_uuid = d.pop("template_uuid", UNSET)
        template_uuid: UUID | Unset
        if isinstance(_template_uuid, Unset):
            template_uuid = UNSET
        else:
            template_uuid = UUID(_template_uuid)

        template_uuid = cls(
            template_uuid=template_uuid,
        )

        template_uuid.additional_properties = d
        return template_uuid

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
