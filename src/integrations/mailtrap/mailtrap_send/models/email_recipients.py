from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.address import Address


T = TypeVar("T", bound="EmailRecipients")


@_attrs_define
class EmailRecipients:
    """
    Attributes:
        to (list[Address] | Unset):
        cc (list[Address] | Unset):
        bcc (list[Address] | Unset):
    """

    to: list[Address] | Unset = UNSET
    cc: list[Address] | Unset = UNSET
    bcc: list[Address] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        to: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.to, Unset):
            to = []
            for to_item_data in self.to:
                to_item = to_item_data.to_dict()
                to.append(to_item)

        cc: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.cc, Unset):
            cc = []
            for cc_item_data in self.cc:
                cc_item = cc_item_data.to_dict()
                cc.append(cc_item)

        bcc: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.bcc, Unset):
            bcc = []
            for bcc_item_data in self.bcc:
                bcc_item = bcc_item_data.to_dict()
                bcc.append(bcc_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if to is not UNSET:
            field_dict["to"] = to
        if cc is not UNSET:
            field_dict["cc"] = cc
        if bcc is not UNSET:
            field_dict["bcc"] = bcc

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.address import Address

        d = dict(src_dict)
        _to = d.pop("to", UNSET)
        to: list[Address] | Unset = UNSET
        if _to is not UNSET:
            to = []
            for to_item_data in _to:
                to_item = Address.from_dict(to_item_data)

                to.append(to_item)

        _cc = d.pop("cc", UNSET)
        cc: list[Address] | Unset = UNSET
        if _cc is not UNSET:
            cc = []
            for cc_item_data in _cc:
                cc_item = Address.from_dict(cc_item_data)

                cc.append(cc_item)

        _bcc = d.pop("bcc", UNSET)
        bcc: list[Address] | Unset = UNSET
        if _bcc is not UNSET:
            bcc = []
            for bcc_item_data in _bcc:
                bcc_item = Address.from_dict(bcc_item_data)

                bcc.append(bcc_item)

        email_recipients = cls(
            to=to,
            cc=cc,
            bcc=bcc,
        )

        email_recipients.additional_properties = d
        return email_recipients

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
