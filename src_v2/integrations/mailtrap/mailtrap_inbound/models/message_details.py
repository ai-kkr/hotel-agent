from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.attachment import Attachment
    from ..models.message_headers_type_0 import MessageHeadersType0


T = TypeVar("T", bound="MessageDetails")


@_attrs_define
class MessageDetails:
    """
    Attributes:
        id (str | Unset): Mailtrap object ID for the message (not the `Message-ID` header value). Example:
            1700000000000123.
        inbox_id (int | Unset):  Example: 1.
        from_ (None | str | Unset):  Example: sender@example.com.
        to (list[str] | Unset):  Example: ['support-tickets-1a2b3c4d@inbound-mailtrap.io'].
        cc (list[str] | Unset):
        bcc (list[str] | Unset):
        reply_to (None | str | Unset):
        subject (None | str | Unset):  Example: Hello.
        message_id (None | str | Unset): Value of the original `Message-ID` header. Example: <abc@sender.example>.
        in_reply_to (None | str | Unset):
        references (list[str] | Unset):
        headers (MessageHeadersType0 | None | Unset): Selected headers from the original message, lowercased.
             Example: {'mime-version': '1.0', 'return-path': '<sender@example.com>'}.
        size (int | None | Unset): Total size of the raw message in bytes. Example: 4096.
        html_size (int | None | Unset): Size of the HTML body in bytes. Zero if the message has no HTML part. Example:
            512.
        text_size (int | None | Unset): Size of the plain-text body in bytes. Zero if the message has no text part.
            Example: 128.
        received_at (datetime.datetime | Unset):  Example: 2026-05-08T10:30:00.000Z.
        attachments (list[Attachment] | Unset):
        raw_message_url (None | str | Unset): Presigned URL to download the raw `.eml` file. Expires after
            one hour.
             Example: https://s3.amazonaws.com/inbound-mail/raw.eml?X-Amz-Signature=....
        raw_message_expires_at (datetime.datetime | None | Unset):  Example: 2026-05-08T11:30:00.000Z.
        html_body (None | str | Unset): Decoded HTML body. `null` when the message has no HTML part. Example:
            <html><body>Hello</body></html>.
        text_body (None | str | Unset): Decoded plain-text body. `null` when the message has no text part. Example:
            Hello.
    """

    id: str | Unset = UNSET
    inbox_id: int | Unset = UNSET
    from_: None | str | Unset = UNSET
    to: list[str] | Unset = UNSET
    cc: list[str] | Unset = UNSET
    bcc: list[str] | Unset = UNSET
    reply_to: None | str | Unset = UNSET
    subject: None | str | Unset = UNSET
    message_id: None | str | Unset = UNSET
    in_reply_to: None | str | Unset = UNSET
    references: list[str] | Unset = UNSET
    headers: MessageHeadersType0 | None | Unset = UNSET
    size: int | None | Unset = UNSET
    html_size: int | None | Unset = UNSET
    text_size: int | None | Unset = UNSET
    received_at: datetime.datetime | Unset = UNSET
    attachments: list[Attachment] | Unset = UNSET
    raw_message_url: None | str | Unset = UNSET
    raw_message_expires_at: datetime.datetime | None | Unset = UNSET
    html_body: None | str | Unset = UNSET
    text_body: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.message_headers_type_0 import MessageHeadersType0

        id = self.id

        inbox_id = self.inbox_id

        from_: None | str | Unset
        if isinstance(self.from_, Unset):
            from_ = UNSET
        else:
            from_ = self.from_

        to: list[str] | Unset = UNSET
        if not isinstance(self.to, Unset):
            to = self.to

        cc: list[str] | Unset = UNSET
        if not isinstance(self.cc, Unset):
            cc = self.cc

        bcc: list[str] | Unset = UNSET
        if not isinstance(self.bcc, Unset):
            bcc = self.bcc

        reply_to: None | str | Unset
        if isinstance(self.reply_to, Unset):
            reply_to = UNSET
        else:
            reply_to = self.reply_to

        subject: None | str | Unset
        if isinstance(self.subject, Unset):
            subject = UNSET
        else:
            subject = self.subject

        message_id: None | str | Unset
        if isinstance(self.message_id, Unset):
            message_id = UNSET
        else:
            message_id = self.message_id

        in_reply_to: None | str | Unset
        if isinstance(self.in_reply_to, Unset):
            in_reply_to = UNSET
        else:
            in_reply_to = self.in_reply_to

        references: list[str] | Unset = UNSET
        if not isinstance(self.references, Unset):
            references = self.references

        headers: dict[str, Any] | None | Unset
        if isinstance(self.headers, Unset):
            headers = UNSET
        elif isinstance(self.headers, MessageHeadersType0):
            headers = self.headers.to_dict()
        else:
            headers = self.headers

        size: int | None | Unset
        if isinstance(self.size, Unset):
            size = UNSET
        else:
            size = self.size

        html_size: int | None | Unset
        if isinstance(self.html_size, Unset):
            html_size = UNSET
        else:
            html_size = self.html_size

        text_size: int | None | Unset
        if isinstance(self.text_size, Unset):
            text_size = UNSET
        else:
            text_size = self.text_size

        received_at: str | Unset = UNSET
        if not isinstance(self.received_at, Unset):
            received_at = self.received_at.isoformat()

        attachments: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.attachments, Unset):
            attachments = []
            for attachments_item_data in self.attachments:
                attachments_item = attachments_item_data.to_dict()
                attachments.append(attachments_item)

        raw_message_url: None | str | Unset
        if isinstance(self.raw_message_url, Unset):
            raw_message_url = UNSET
        else:
            raw_message_url = self.raw_message_url

        raw_message_expires_at: None | str | Unset
        if isinstance(self.raw_message_expires_at, Unset):
            raw_message_expires_at = UNSET
        elif isinstance(self.raw_message_expires_at, datetime.datetime):
            raw_message_expires_at = self.raw_message_expires_at.isoformat()
        else:
            raw_message_expires_at = self.raw_message_expires_at

        html_body: None | str | Unset
        if isinstance(self.html_body, Unset):
            html_body = UNSET
        else:
            html_body = self.html_body

        text_body: None | str | Unset
        if isinstance(self.text_body, Unset):
            text_body = UNSET
        else:
            text_body = self.text_body

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if inbox_id is not UNSET:
            field_dict["inbox_id"] = inbox_id
        if from_ is not UNSET:
            field_dict["from"] = from_
        if to is not UNSET:
            field_dict["to"] = to
        if cc is not UNSET:
            field_dict["cc"] = cc
        if bcc is not UNSET:
            field_dict["bcc"] = bcc
        if reply_to is not UNSET:
            field_dict["reply_to"] = reply_to
        if subject is not UNSET:
            field_dict["subject"] = subject
        if message_id is not UNSET:
            field_dict["message_id"] = message_id
        if in_reply_to is not UNSET:
            field_dict["in_reply_to"] = in_reply_to
        if references is not UNSET:
            field_dict["references"] = references
        if headers is not UNSET:
            field_dict["headers"] = headers
        if size is not UNSET:
            field_dict["size"] = size
        if html_size is not UNSET:
            field_dict["html_size"] = html_size
        if text_size is not UNSET:
            field_dict["text_size"] = text_size
        if received_at is not UNSET:
            field_dict["received_at"] = received_at
        if attachments is not UNSET:
            field_dict["attachments"] = attachments
        if raw_message_url is not UNSET:
            field_dict["raw_message_url"] = raw_message_url
        if raw_message_expires_at is not UNSET:
            field_dict["raw_message_expires_at"] = raw_message_expires_at
        if html_body is not UNSET:
            field_dict["html_body"] = html_body
        if text_body is not UNSET:
            field_dict["text_body"] = text_body

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.attachment import Attachment
        from ..models.message_headers_type_0 import MessageHeadersType0

        d = dict(src_dict)
        id = d.pop("id", UNSET)

        inbox_id = d.pop("inbox_id", UNSET)

        def _parse_from_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        from_ = _parse_from_(d.pop("from", UNSET))

        to = cast(list[str], d.pop("to", UNSET))

        cc = cast(list[str], d.pop("cc", UNSET))

        bcc = cast(list[str], d.pop("bcc", UNSET))

        def _parse_reply_to(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        reply_to = _parse_reply_to(d.pop("reply_to", UNSET))

        def _parse_subject(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        subject = _parse_subject(d.pop("subject", UNSET))

        def _parse_message_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        message_id = _parse_message_id(d.pop("message_id", UNSET))

        def _parse_in_reply_to(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        in_reply_to = _parse_in_reply_to(d.pop("in_reply_to", UNSET))

        references = cast(list[str], d.pop("references", UNSET))

        def _parse_headers(data: object) -> MessageHeadersType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                headers_type_0 = MessageHeadersType0.from_dict(data)

                return headers_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(MessageHeadersType0 | None | Unset, data)

        headers = _parse_headers(d.pop("headers", UNSET))

        def _parse_size(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        size = _parse_size(d.pop("size", UNSET))

        def _parse_html_size(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        html_size = _parse_html_size(d.pop("html_size", UNSET))

        def _parse_text_size(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        text_size = _parse_text_size(d.pop("text_size", UNSET))

        _received_at = d.pop("received_at", UNSET)
        received_at: datetime.datetime | Unset
        if isinstance(_received_at, Unset):
            received_at = UNSET
        else:
            received_at = datetime.datetime.fromisoformat(_received_at)

        _attachments = d.pop("attachments", UNSET)
        attachments: list[Attachment] | Unset = UNSET
        if _attachments is not UNSET:
            attachments = []
            for attachments_item_data in _attachments:
                attachments_item = Attachment.from_dict(attachments_item_data)

                attachments.append(attachments_item)

        def _parse_raw_message_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        raw_message_url = _parse_raw_message_url(d.pop("raw_message_url", UNSET))

        def _parse_raw_message_expires_at(
            data: object,
        ) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                raw_message_expires_at_type_0 = datetime.datetime.fromisoformat(data)

                return raw_message_expires_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        raw_message_expires_at = _parse_raw_message_expires_at(
            d.pop("raw_message_expires_at", UNSET)
        )

        def _parse_html_body(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        html_body = _parse_html_body(d.pop("html_body", UNSET))

        def _parse_text_body(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        text_body = _parse_text_body(d.pop("text_body", UNSET))

        message_details = cls(
            id=id,
            inbox_id=inbox_id,
            from_=from_,
            to=to,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            subject=subject,
            message_id=message_id,
            in_reply_to=in_reply_to,
            references=references,
            headers=headers,
            size=size,
            html_size=html_size,
            text_size=text_size,
            received_at=received_at,
            attachments=attachments,
            raw_message_url=raw_message_url,
            raw_message_expires_at=raw_message_expires_at,
            html_body=html_body,
            text_body=text_body,
        )

        message_details.additional_properties = d
        return message_details

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
