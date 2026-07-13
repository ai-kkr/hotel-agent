from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.attachment_content_disposition_type_1 import (
    AttachmentContentDispositionType1,
)
from ..models.attachment_content_disposition_type_2_type_1 import (
    AttachmentContentDispositionType2Type1,
)
from ..models.attachment_content_disposition_type_3_type_1 import (
    AttachmentContentDispositionType3Type1,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="Attachment")


@_attrs_define
class Attachment:
    """
    Attributes:
        attachment_id (str | Unset):  Example: att-1.
        size (int | None | Unset):  Example: 1024.
        filename (None | str | Unset):  Example: logo.png.
        content_type (None | str | Unset):  Example: image/png.
        content_disposition (AttachmentContentDispositionType1 | AttachmentContentDispositionType2Type1 |
            AttachmentContentDispositionType3Type1 | None | Unset):  Example: inline.
        content_id (None | str | Unset): `Content-ID` header value, used to reference inline attachments
            from the HTML body.
             Example: logo@example.com.
    """

    attachment_id: str | Unset = UNSET
    size: int | None | Unset = UNSET
    filename: None | str | Unset = UNSET
    content_type: None | str | Unset = UNSET
    content_disposition: (
        AttachmentContentDispositionType1
        | AttachmentContentDispositionType2Type1
        | AttachmentContentDispositionType3Type1
        | None
        | Unset
    ) = UNSET
    content_id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        attachment_id = self.attachment_id

        size: int | None | Unset
        if isinstance(self.size, Unset):
            size = UNSET
        else:
            size = self.size

        filename: None | str | Unset
        if isinstance(self.filename, Unset):
            filename = UNSET
        else:
            filename = self.filename

        content_type: None | str | Unset
        if isinstance(self.content_type, Unset):
            content_type = UNSET
        else:
            content_type = self.content_type

        content_disposition: None | str | Unset
        if isinstance(self.content_disposition, Unset):
            content_disposition = UNSET
        elif isinstance(self.content_disposition, AttachmentContentDispositionType1):
            content_disposition = self.content_disposition.value
        elif isinstance(
            self.content_disposition, AttachmentContentDispositionType2Type1
        ):
            content_disposition = self.content_disposition.value
        elif isinstance(
            self.content_disposition, AttachmentContentDispositionType3Type1
        ):
            content_disposition = self.content_disposition.value
        else:
            content_disposition = self.content_disposition

        content_id: None | str | Unset
        if isinstance(self.content_id, Unset):
            content_id = UNSET
        else:
            content_id = self.content_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if attachment_id is not UNSET:
            field_dict["attachment_id"] = attachment_id
        if size is not UNSET:
            field_dict["size"] = size
        if filename is not UNSET:
            field_dict["filename"] = filename
        if content_type is not UNSET:
            field_dict["content_type"] = content_type
        if content_disposition is not UNSET:
            field_dict["content_disposition"] = content_disposition
        if content_id is not UNSET:
            field_dict["content_id"] = content_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        attachment_id = d.pop("attachment_id", UNSET)

        def _parse_size(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        size = _parse_size(d.pop("size", UNSET))

        def _parse_filename(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        filename = _parse_filename(d.pop("filename", UNSET))

        def _parse_content_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        content_type = _parse_content_type(d.pop("content_type", UNSET))

        def _parse_content_disposition(
            data: object,
        ) -> (
            AttachmentContentDispositionType1
            | AttachmentContentDispositionType2Type1
            | AttachmentContentDispositionType3Type1
            | None
            | Unset
        ):
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                content_disposition_type_1 = AttachmentContentDispositionType1(data)

                return content_disposition_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, str):
                    raise TypeError()
                content_disposition_type_2_type_1 = (
                    AttachmentContentDispositionType2Type1(data)
                )

                return content_disposition_type_2_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, str):
                    raise TypeError()
                content_disposition_type_3_type_1 = (
                    AttachmentContentDispositionType3Type1(data)
                )

                return content_disposition_type_3_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(
                AttachmentContentDispositionType1
                | AttachmentContentDispositionType2Type1
                | AttachmentContentDispositionType3Type1
                | None
                | Unset,
                data,
            )

        content_disposition = _parse_content_disposition(
            d.pop("content_disposition", UNSET)
        )

        def _parse_content_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        content_id = _parse_content_id(d.pop("content_id", UNSET))

        attachment = cls(
            attachment_id=attachment_id,
            size=size,
            filename=filename,
            content_type=content_type,
            content_disposition=content_disposition,
            content_id=content_id,
        )

        attachment.additional_properties = d
        return attachment

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
