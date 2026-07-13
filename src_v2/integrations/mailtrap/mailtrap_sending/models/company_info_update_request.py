from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.company_info_update_request_info_level import (
    CompanyInfoUpdateRequestInfoLevel,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="CompanyInfoUpdateRequest")


@_attrs_define
class CompanyInfoUpdateRequest:
    """All fields are optional. Only the fields provided in the request will be updated.

    Attributes:
        name (str | Unset): Company or individual name Example: Mailtrap.
        address (str | Unset): Street address Example: 123 Main St.
        city (str | Unset): City Example: San Francisco.
        country (str | Unset): Country Example: US.
        phone (str | Unset): Phone number Example: +1-555-0100.
        zip_code (str | Unset): ZIP or postal code Example: 94105.
        privacy_policy_url (str | Unset): URL to the privacy policy page Example: https://mailtrap.io/privacy.
        terms_of_service_url (str | Unset): URL to the terms of service page Example: https://mailtrap.io/terms.
        website_url (str | Unset): Company website URL Example: https://mailtrap.io.
        info_level (CompanyInfoUpdateRequestInfoLevel | Unset): Whether the sender is a business or individual Example:
            business.
    """

    name: str | Unset = UNSET
    address: str | Unset = UNSET
    city: str | Unset = UNSET
    country: str | Unset = UNSET
    phone: str | Unset = UNSET
    zip_code: str | Unset = UNSET
    privacy_policy_url: str | Unset = UNSET
    terms_of_service_url: str | Unset = UNSET
    website_url: str | Unset = UNSET
    info_level: CompanyInfoUpdateRequestInfoLevel | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        address = self.address

        city = self.city

        country = self.country

        phone = self.phone

        zip_code = self.zip_code

        privacy_policy_url = self.privacy_policy_url

        terms_of_service_url = self.terms_of_service_url

        website_url = self.website_url

        info_level: str | Unset = UNSET
        if not isinstance(self.info_level, Unset):
            info_level = self.info_level.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if address is not UNSET:
            field_dict["address"] = address
        if city is not UNSET:
            field_dict["city"] = city
        if country is not UNSET:
            field_dict["country"] = country
        if phone is not UNSET:
            field_dict["phone"] = phone
        if zip_code is not UNSET:
            field_dict["zip_code"] = zip_code
        if privacy_policy_url is not UNSET:
            field_dict["privacy_policy_url"] = privacy_policy_url
        if terms_of_service_url is not UNSET:
            field_dict["terms_of_service_url"] = terms_of_service_url
        if website_url is not UNSET:
            field_dict["website_url"] = website_url
        if info_level is not UNSET:
            field_dict["info_level"] = info_level

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name", UNSET)

        address = d.pop("address", UNSET)

        city = d.pop("city", UNSET)

        country = d.pop("country", UNSET)

        phone = d.pop("phone", UNSET)

        zip_code = d.pop("zip_code", UNSET)

        privacy_policy_url = d.pop("privacy_policy_url", UNSET)

        terms_of_service_url = d.pop("terms_of_service_url", UNSET)

        website_url = d.pop("website_url", UNSET)

        _info_level = d.pop("info_level", UNSET)
        info_level: CompanyInfoUpdateRequestInfoLevel | Unset
        if isinstance(_info_level, Unset):
            info_level = UNSET
        else:
            info_level = CompanyInfoUpdateRequestInfoLevel(_info_level)

        company_info_update_request = cls(
            name=name,
            address=address,
            city=city,
            country=country,
            phone=phone,
            zip_code=zip_code,
            privacy_policy_url=privacy_policy_url,
            terms_of_service_url=terms_of_service_url,
            website_url=website_url,
            info_level=info_level,
        )

        company_info_update_request.additional_properties = d
        return company_info_update_request

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
