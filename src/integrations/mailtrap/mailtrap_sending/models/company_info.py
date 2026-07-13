from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.company_info_info_level import CompanyInfoInfoLevel
from ..types import UNSET, Unset

T = TypeVar("T", bound="CompanyInfo")


@_attrs_define
class CompanyInfo:
    """
    Example:
        {'name': 'Mailtrap', 'address': '123 Main St', 'city': 'San Francisco', 'country': 'US', 'phone': '+1-555-0100',
            'zip_code': '94105', 'privacy_policy_url': 'https://mailtrap.io/privacy', 'terms_of_service_url':
            'https://mailtrap.io/terms', 'website_url': 'https://mailtrap.io', 'info_level': 'business'}

    Attributes:
        name (None | str | Unset): Company or individual name
        address (None | str | Unset): Street address
        city (None | str | Unset): City
        country (None | str | Unset): Country
        phone (None | str | Unset): Phone number
        zip_code (None | str | Unset): ZIP or postal code
        privacy_policy_url (None | str | Unset): URL to the privacy policy page
        terms_of_service_url (None | str | Unset): URL to the terms of service page
        website_url (None | str | Unset): Company website URL or LinkedIn / personal website
        info_level (CompanyInfoInfoLevel | Unset): Whether the sender is a business or individual
    """

    name: None | str | Unset = UNSET
    address: None | str | Unset = UNSET
    city: None | str | Unset = UNSET
    country: None | str | Unset = UNSET
    phone: None | str | Unset = UNSET
    zip_code: None | str | Unset = UNSET
    privacy_policy_url: None | str | Unset = UNSET
    terms_of_service_url: None | str | Unset = UNSET
    website_url: None | str | Unset = UNSET
    info_level: CompanyInfoInfoLevel | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        address: None | str | Unset
        if isinstance(self.address, Unset):
            address = UNSET
        else:
            address = self.address

        city: None | str | Unset
        if isinstance(self.city, Unset):
            city = UNSET
        else:
            city = self.city

        country: None | str | Unset
        if isinstance(self.country, Unset):
            country = UNSET
        else:
            country = self.country

        phone: None | str | Unset
        if isinstance(self.phone, Unset):
            phone = UNSET
        else:
            phone = self.phone

        zip_code: None | str | Unset
        if isinstance(self.zip_code, Unset):
            zip_code = UNSET
        else:
            zip_code = self.zip_code

        privacy_policy_url: None | str | Unset
        if isinstance(self.privacy_policy_url, Unset):
            privacy_policy_url = UNSET
        else:
            privacy_policy_url = self.privacy_policy_url

        terms_of_service_url: None | str | Unset
        if isinstance(self.terms_of_service_url, Unset):
            terms_of_service_url = UNSET
        else:
            terms_of_service_url = self.terms_of_service_url

        website_url: None | str | Unset
        if isinstance(self.website_url, Unset):
            website_url = UNSET
        else:
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

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

        def _parse_address(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        address = _parse_address(d.pop("address", UNSET))

        def _parse_city(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        city = _parse_city(d.pop("city", UNSET))

        def _parse_country(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        country = _parse_country(d.pop("country", UNSET))

        def _parse_phone(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        phone = _parse_phone(d.pop("phone", UNSET))

        def _parse_zip_code(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        zip_code = _parse_zip_code(d.pop("zip_code", UNSET))

        def _parse_privacy_policy_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        privacy_policy_url = _parse_privacy_policy_url(
            d.pop("privacy_policy_url", UNSET)
        )

        def _parse_terms_of_service_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        terms_of_service_url = _parse_terms_of_service_url(
            d.pop("terms_of_service_url", UNSET)
        )

        def _parse_website_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        website_url = _parse_website_url(d.pop("website_url", UNSET))

        _info_level = d.pop("info_level", UNSET)
        info_level: CompanyInfoInfoLevel | Unset
        if isinstance(_info_level, Unset):
            info_level = UNSET
        else:
            info_level = CompanyInfoInfoLevel(_info_level)

        company_info = cls(
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

        company_info.additional_properties = d
        return company_info

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
