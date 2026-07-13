from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.email_sending_headers_headers import EmailSendingHeadersHeaders


T = TypeVar("T", bound="EmailSendingHeaders")


@_attrs_define
class EmailSendingHeaders:
    """
    Attributes:
        headers (EmailSendingHeadersHeaders | Unset):  Example: {'X-Message-Source': 'api.example.com', 'X-Campaign-ID':
            'CAMP-123'}.
    """

    headers: EmailSendingHeadersHeaders | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        headers: dict[str, Any] | Unset = UNSET
        if not isinstance(self.headers, Unset):
            headers = self.headers.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if headers is not UNSET:
            field_dict["headers"] = headers

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.email_sending_headers_headers import EmailSendingHeadersHeaders

        d = dict(src_dict)
        _headers = d.pop("headers", UNSET)
        headers: EmailSendingHeadersHeaders | Unset
        if isinstance(_headers, Unset):
            headers = UNSET
        else:
            headers = EmailSendingHeadersHeaders.from_dict(_headers)

        email_sending_headers = cls(
            headers=headers,
        )

        email_sending_headers.additional_properties = d
        return email_sending_headers

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
