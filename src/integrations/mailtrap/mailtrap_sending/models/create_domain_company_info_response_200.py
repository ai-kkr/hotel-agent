from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.company_info import CompanyInfo


T = TypeVar("T", bound="CreateDomainCompanyInfoResponse200")


@_attrs_define
class CreateDomainCompanyInfoResponse200:
    """
    Attributes:
        data (CompanyInfo | Unset):  Example: {'name': 'Mailtrap', 'address': '123 Main St', 'city': 'San Francisco',
            'country': 'US', 'phone': '+1-555-0100', 'zip_code': '94105', 'privacy_policy_url':
            'https://mailtrap.io/privacy', 'terms_of_service_url': 'https://mailtrap.io/terms', 'website_url':
            'https://mailtrap.io', 'info_level': 'business'}.
    """

    data: CompanyInfo | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] | Unset = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.company_info import CompanyInfo

        d = dict(src_dict)
        _data = d.pop("data", UNSET)
        data: CompanyInfo | Unset
        if isinstance(_data, Unset):
            data = UNSET
        else:
            data = CompanyInfo.from_dict(_data)

        create_domain_company_info_response_200 = cls(
            data=data,
        )

        create_domain_company_info_response_200.additional_properties = d
        return create_domain_company_info_response_200

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
