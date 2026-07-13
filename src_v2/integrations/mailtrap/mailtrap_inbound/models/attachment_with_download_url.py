from __future__ import annotations

import datetime
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

T = TypeVar("T", bound="AttachmentWithDownloadUrl")


@_attrs_define
class AttachmentWithDownloadUrl:
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
        download_url (None | str | Unset): Presigned URL to download the attachment. Expires after one hour. Example:
            https://s3.amazonaws.com/inbound-mail/att-1?X-Amz-Signature=....
        download_url_expires_at (datetime.datetime | None | Unset):  Example: 2026-05-08T11:30:00.000Z.
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
    download_url: None | str | Unset = UNSET
    download_url_expires_at: datetime.datetime | None | Unset = UNSET
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

        download_url: None | str | Unset
        if isinstance(self.download_url, Unset):
            download_url = UNSET
        else:
            download_url = self.download_url

        download_url_expires_at: None | str | Unset
        if isinstance(self.download_url_expires_at, Unset):
            download_url_expires_at = UNSET
        elif isinstance(self.download_url_expires_at, datetime.datetime):
            download_url_expires_at = self.download_url_expires_at.isoformat()
        else:
            download_url_expires_at = self.download_url_expires_at

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
        if download_url is not UNSET:
            field_dict["download_url"] = download_url
        if download_url_expires_at is not UNSET:
            field_dict["download_url_expires_at"] = download_url_expires_at

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

        def _parse_download_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        download_url = _parse_download_url(d.pop("download_url", UNSET))

        def _parse_download_url_expires_at(
            data: object,
        ) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                download_url_expires_at_type_0 = datetime.datetime.fromisoformat(data)

                return download_url_expires_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        download_url_expires_at = _parse_download_url_expires_at(
            d.pop("download_url_expires_at", UNSET)
        )

        attachment_with_download_url = cls(
            attachment_id=attachment_id,
            size=size,
            filename=filename,
            content_type=content_type,
            content_disposition=content_disposition,
            content_id=content_id,
            download_url=download_url,
            download_url_expires_at=download_url_expires_at,
        )

        attachment_with_download_url.additional_properties = d
        return attachment_with_download_url

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
