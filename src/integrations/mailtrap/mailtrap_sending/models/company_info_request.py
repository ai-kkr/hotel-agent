from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.company_info_request_info_level import CompanyInfoRequestInfoLevel
from ..types import UNSET, Unset

T = TypeVar("T", bound="CompanyInfoRequest")


@_attrs_define
class CompanyInfoRequest:
    """
    Attributes:
        name (str): Company or individual name Example: Mailtrap.
        address (str): Street address Example: 123 Main St.
        city (str): City Example: San Francisco.
        country (str): Country Example: US.
        zip_code (str): ZIP or postal code Example: 94105.
        website_url (str): Company website URL Example: https://mailtrap.io.
        phone (str | Unset): Phone number Example: +1-555-0100.
        privacy_policy_url (str | Unset): URL to the privacy policy page Example: https://mailtrap.io/privacy.
        terms_of_service_url (str | Unset): URL to the terms of service page Example: https://mailtrap.io/terms.
        info_level (CompanyInfoRequestInfoLevel | Unset): Whether the sender is a business or individual Example:
            business.
    """

    name: str
    address: str
    city: str
    country: str
    zip_code: str
    website_url: str
    phone: str | Unset = UNSET
    privacy_policy_url: str | Unset = UNSET
    terms_of_service_url: str | Unset = UNSET
    info_level: CompanyInfoRequestInfoLevel | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        address = self.address

        city = self.city

        country = self.country

        zip_code = self.zip_code

        website_url = self.website_url

        phone = self.phone

        privacy_policy_url = self.privacy_policy_url

        terms_of_service_url = self.terms_of_service_url

        info_level: str | Unset = UNSET
        if not isinstance(self.info_level, Unset):
            info_level = self.info_level.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "address": address,
                "city": city,
                "country": country,
                "zip_code": zip_code,
                "website_url": website_url,
            }
        )
        if phone is not UNSET:
            field_dict["phone"] = phone
        if privacy_policy_url is not UNSET:
            field_dict["privacy_policy_url"] = privacy_policy_url
        if terms_of_service_url is not UNSET:
            field_dict["terms_of_service_url"] = terms_of_service_url
        if info_level is not UNSET:
            field_dict["info_level"] = info_level

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        address = d.pop("address")

        city = d.pop("city")

        country = d.pop("country")

        zip_code = d.pop("zip_code")

        website_url = d.pop("website_url")

        phone = d.pop("phone", UNSET)

        privacy_policy_url = d.pop("privacy_policy_url", UNSET)

        terms_of_service_url = d.pop("terms_of_service_url", UNSET)

        _info_level = d.pop("info_level", UNSET)
        info_level: CompanyInfoRequestInfoLevel | Unset
        if isinstance(_info_level, Unset):
            info_level = UNSET
        else:
            info_level = CompanyInfoRequestInfoLevel(_info_level)

        company_info_request = cls(
            name=name,
            address=address,
            city=city,
            country=country,
            zip_code=zip_code,
            website_url=website_url,
            phone=phone,
            privacy_policy_url=privacy_policy_url,
            terms_of_service_url=terms_of_service_url,
            info_level=info_level,
        )

        company_info_request.additional_properties = d
        return company_info_request

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
