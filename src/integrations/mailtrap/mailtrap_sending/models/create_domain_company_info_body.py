from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.company_info_request import CompanyInfoRequest


T = TypeVar("T", bound="CreateDomainCompanyInfoBody")


@_attrs_define
class CreateDomainCompanyInfoBody:
    """
    Attributes:
        company_info (CompanyInfoRequest):
    """

    company_info: CompanyInfoRequest
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        company_info = self.company_info.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "company_info": company_info,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.company_info_request import CompanyInfoRequest

        d = dict(src_dict)
        company_info = CompanyInfoRequest.from_dict(d.pop("company_info"))

        create_domain_company_info_body = cls(
            company_info=company_info,
        )

        create_domain_company_info_body.additional_properties = d
        return create_domain_company_info_body

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
