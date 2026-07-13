from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.domain_dns_records_item_status import DomainDnsRecordsItemStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="DomainDnsRecordsItem")


@_attrs_define
class DomainDnsRecordsItem:
    """
    Attributes:
        key (str | Unset):
        domain (str | Unset):
        name (str | Unset):
        status (DomainDnsRecordsItemStatus | Unset):
        type_ (str | Unset):
        value (str | Unset):
    """

    key: str | Unset = UNSET
    domain: str | Unset = UNSET
    name: str | Unset = UNSET
    status: DomainDnsRecordsItemStatus | Unset = UNSET
    type_: str | Unset = UNSET
    value: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        key = self.key

        domain = self.domain

        name = self.name

        status: str | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        type_ = self.type_

        value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if key is not UNSET:
            field_dict["key"] = key
        if domain is not UNSET:
            field_dict["domain"] = domain
        if name is not UNSET:
            field_dict["name"] = name
        if status is not UNSET:
            field_dict["status"] = status
        if type_ is not UNSET:
            field_dict["type"] = type_
        if value is not UNSET:
            field_dict["value"] = value

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        key = d.pop("key", UNSET)

        domain = d.pop("domain", UNSET)

        name = d.pop("name", UNSET)

        _status = d.pop("status", UNSET)
        status: DomainDnsRecordsItemStatus | Unset
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = DomainDnsRecordsItemStatus(_status)

        type_ = d.pop("type", UNSET)

        value = d.pop("value", UNSET)

        domain_dns_records_item = cls(
            key=key,
            domain=domain,
            name=name,
            status=status,
            type_=type_,
            value=value,
        )

        domain_dns_records_item.additional_properties = d
        return domain_dns_records_item

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
