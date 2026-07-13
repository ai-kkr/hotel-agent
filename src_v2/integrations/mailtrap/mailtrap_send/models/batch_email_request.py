from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.batch_email_request_base import BatchEmailRequestBase
    from ..models.batch_email_request_requests_item import BatchEmailRequestRequestsItem


T = TypeVar("T", bound="BatchEmailRequest")


@_attrs_define
class BatchEmailRequest:
    """Send multiple emails in a single API call (up to 500)

    Attributes:
        requests (list[BatchEmailRequestRequestsItem]): Individual email configurations (max 500)
        base (BatchEmailRequestBase | Unset): Base properties shared by all emails
    """

    requests: list[BatchEmailRequestRequestsItem]
    base: BatchEmailRequestBase | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        requests = []
        for requests_item_data in self.requests:
            requests_item = requests_item_data.to_dict()
            requests.append(requests_item)

        base: dict[str, Any] | Unset = UNSET
        if not isinstance(self.base, Unset):
            base = self.base.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "requests": requests,
            }
        )
        if base is not UNSET:
            field_dict["base"] = base

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.batch_email_request_base import BatchEmailRequestBase
        from ..models.batch_email_request_requests_item import (
            BatchEmailRequestRequestsItem,
        )

        d = dict(src_dict)
        requests = []
        _requests = d.pop("requests")
        for requests_item_data in _requests:
            requests_item = BatchEmailRequestRequestsItem.from_dict(requests_item_data)

            requests.append(requests_item)

        _base = d.pop("base", UNSET)
        base: BatchEmailRequestBase | Unset
        if isinstance(_base, Unset):
            base = UNSET
        else:
            base = BatchEmailRequestBase.from_dict(_base)

        batch_email_request = cls(
            requests=requests,
            base=base,
        )

        batch_email_request.additional_properties = d
        return batch_email_request

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
