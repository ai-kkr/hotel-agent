from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.address import Address


T = TypeVar("T", bound="EmailReplyTo")


@_attrs_define
class EmailReplyTo:
    """
    Attributes:
        reply_to (Address | Unset):
    """

    reply_to: Address | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        reply_to: dict[str, Any] | Unset = UNSET
        if not isinstance(self.reply_to, Unset):
            reply_to = self.reply_to.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if reply_to is not UNSET:
            field_dict["reply_to"] = reply_to

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.address import Address

        d = dict(src_dict)
        _reply_to = d.pop("reply_to", UNSET)
        reply_to: Address | Unset
        if isinstance(_reply_to, Unset):
            reply_to = UNSET
        else:
            reply_to = Address.from_dict(_reply_to)

        email_reply_to = cls(
            reply_to=reply_to,
        )

        email_reply_to.additional_properties = d
        return email_reply_to

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
