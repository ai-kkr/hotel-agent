from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.email_attachments_attachments_item_disposition import (
    EmailAttachmentsAttachmentsItemDisposition,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="EmailAttachmentsAttachmentsItem")


@_attrs_define
class EmailAttachmentsAttachmentsItem:
    """
    Attributes:
        content (str): Base64 encoded content Example: base64encodedcontent==.
        filename (str):  Example: document.pdf.
        type_ (str | Unset): MIME type Example: application/pdf.
        disposition (EmailAttachmentsAttachmentsItemDisposition | Unset):  Default:
            EmailAttachmentsAttachmentsItemDisposition.ATTACHMENT.
        content_id (str | Unset): For inline attachments Example: image001.
    """

    content: str
    filename: str
    type_: str | Unset = UNSET
    disposition: EmailAttachmentsAttachmentsItemDisposition | Unset = (
        EmailAttachmentsAttachmentsItemDisposition.ATTACHMENT
    )
    content_id: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        content = self.content

        filename = self.filename

        type_ = self.type_

        disposition: str | Unset = UNSET
        if not isinstance(self.disposition, Unset):
            disposition = self.disposition.value

        content_id = self.content_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "content": content,
                "filename": filename,
            }
        )
        if type_ is not UNSET:
            field_dict["type"] = type_
        if disposition is not UNSET:
            field_dict["disposition"] = disposition
        if content_id is not UNSET:
            field_dict["content_id"] = content_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        content = d.pop("content")

        filename = d.pop("filename")

        type_ = d.pop("type", UNSET)

        _disposition = d.pop("disposition", UNSET)
        disposition: EmailAttachmentsAttachmentsItemDisposition | Unset
        if isinstance(_disposition, Unset):
            disposition = UNSET
        else:
            disposition = EmailAttachmentsAttachmentsItemDisposition(_disposition)

        content_id = d.pop("content_id", UNSET)

        email_attachments_attachments_item = cls(
            content=content,
            filename=filename,
            type_=type_,
            disposition=disposition,
            content_id=content_id,
        )

        email_attachments_attachments_item.additional_properties = d
        return email_attachments_attachments_item

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
