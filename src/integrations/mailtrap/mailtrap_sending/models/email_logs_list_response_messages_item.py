from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.email_logs_list_response_messages_item_sending_stream import (
    EmailLogsListResponseMessagesItemSendingStream,
)
from ..models.email_logs_list_response_messages_item_status import (
    EmailLogsListResponseMessagesItemStatus,
)
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.email_logs_list_response_messages_item_custom_variables import (
        EmailLogsListResponseMessagesItemCustomVariables,
    )
    from ..models.email_logs_list_response_messages_item_template_variables import (
        EmailLogsListResponseMessagesItemTemplateVariables,
    )


T = TypeVar("T", bound="EmailLogsListResponseMessagesItem")


@_attrs_define
class EmailLogsListResponseMessagesItem:
    """
    Attributes:
        message_id (UUID | Unset):
        status (EmailLogsListResponseMessagesItemStatus | Unset):
        subject (None | str | Unset):
        from_ (str | Unset):
        to (str | Unset):
        sent_at (datetime.datetime | Unset):
        client_ip (None | str | Unset):
        category (None | str | Unset):
        custom_variables (EmailLogsListResponseMessagesItemCustomVariables | Unset):
        sending_stream (EmailLogsListResponseMessagesItemSendingStream | Unset):
        domain_id (int | Unset):
        template_id (int | None | Unset):
        template_variables (EmailLogsListResponseMessagesItemTemplateVariables | Unset):
        opens_count (int | Unset):
        clicks_count (int | Unset):
    """

    message_id: UUID | Unset = UNSET
    status: EmailLogsListResponseMessagesItemStatus | Unset = UNSET
    subject: None | str | Unset = UNSET
    from_: str | Unset = UNSET
    to: str | Unset = UNSET
    sent_at: datetime.datetime | Unset = UNSET
    client_ip: None | str | Unset = UNSET
    category: None | str | Unset = UNSET
    custom_variables: EmailLogsListResponseMessagesItemCustomVariables | Unset = UNSET
    sending_stream: EmailLogsListResponseMessagesItemSendingStream | Unset = UNSET
    domain_id: int | Unset = UNSET
    template_id: int | None | Unset = UNSET
    template_variables: EmailLogsListResponseMessagesItemTemplateVariables | Unset = (
        UNSET
    )
    opens_count: int | Unset = UNSET
    clicks_count: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        message_id: str | Unset = UNSET
        if not isinstance(self.message_id, Unset):
            message_id = str(self.message_id)

        status: str | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        subject: None | str | Unset
        if isinstance(self.subject, Unset):
            subject = UNSET
        else:
            subject = self.subject

        from_ = self.from_

        to = self.to

        sent_at: str | Unset = UNSET
        if not isinstance(self.sent_at, Unset):
            sent_at = self.sent_at.isoformat()

        client_ip: None | str | Unset
        if isinstance(self.client_ip, Unset):
            client_ip = UNSET
        else:
            client_ip = self.client_ip

        category: None | str | Unset
        if isinstance(self.category, Unset):
            category = UNSET
        else:
            category = self.category

        custom_variables: dict[str, Any] | Unset = UNSET
        if not isinstance(self.custom_variables, Unset):
            custom_variables = self.custom_variables.to_dict()

        sending_stream: str | Unset = UNSET
        if not isinstance(self.sending_stream, Unset):
            sending_stream = self.sending_stream.value

        domain_id = self.domain_id

        template_id: int | None | Unset
        if isinstance(self.template_id, Unset):
            template_id = UNSET
        else:
            template_id = self.template_id

        template_variables: dict[str, Any] | Unset = UNSET
        if not isinstance(self.template_variables, Unset):
            template_variables = self.template_variables.to_dict()

        opens_count = self.opens_count

        clicks_count = self.clicks_count

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if message_id is not UNSET:
            field_dict["message_id"] = message_id
        if status is not UNSET:
            field_dict["status"] = status
        if subject is not UNSET:
            field_dict["subject"] = subject
        if from_ is not UNSET:
            field_dict["from"] = from_
        if to is not UNSET:
            field_dict["to"] = to
        if sent_at is not UNSET:
            field_dict["sent_at"] = sent_at
        if client_ip is not UNSET:
            field_dict["client_ip"] = client_ip
        if category is not UNSET:
            field_dict["category"] = category
        if custom_variables is not UNSET:
            field_dict["custom_variables"] = custom_variables
        if sending_stream is not UNSET:
            field_dict["sending_stream"] = sending_stream
        if domain_id is not UNSET:
            field_dict["domain_id"] = domain_id
        if template_id is not UNSET:
            field_dict["template_id"] = template_id
        if template_variables is not UNSET:
            field_dict["template_variables"] = template_variables
        if opens_count is not UNSET:
            field_dict["opens_count"] = opens_count
        if clicks_count is not UNSET:
            field_dict["clicks_count"] = clicks_count

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.email_logs_list_response_messages_item_custom_variables import (
            EmailLogsListResponseMessagesItemCustomVariables,
        )
        from ..models.email_logs_list_response_messages_item_template_variables import (
            EmailLogsListResponseMessagesItemTemplateVariables,
        )

        d = dict(src_dict)
        _message_id = d.pop("message_id", UNSET)
        message_id: UUID | Unset
        if isinstance(_message_id, Unset):
            message_id = UNSET
        else:
            message_id = UUID(_message_id)

        _status = d.pop("status", UNSET)
        status: EmailLogsListResponseMessagesItemStatus | Unset
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = EmailLogsListResponseMessagesItemStatus(_status)

        def _parse_subject(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        subject = _parse_subject(d.pop("subject", UNSET))

        from_ = d.pop("from", UNSET)

        to = d.pop("to", UNSET)

        _sent_at = d.pop("sent_at", UNSET)
        sent_at: datetime.datetime | Unset
        if isinstance(_sent_at, Unset):
            sent_at = UNSET
        else:
            sent_at = datetime.datetime.fromisoformat(_sent_at)

        def _parse_client_ip(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        client_ip = _parse_client_ip(d.pop("client_ip", UNSET))

        def _parse_category(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        category = _parse_category(d.pop("category", UNSET))

        _custom_variables = d.pop("custom_variables", UNSET)
        custom_variables: EmailLogsListResponseMessagesItemCustomVariables | Unset
        if isinstance(_custom_variables, Unset):
            custom_variables = UNSET
        else:
            custom_variables = (
                EmailLogsListResponseMessagesItemCustomVariables.from_dict(
                    _custom_variables
                )
            )

        _sending_stream = d.pop("sending_stream", UNSET)
        sending_stream: EmailLogsListResponseMessagesItemSendingStream | Unset
        if isinstance(_sending_stream, Unset):
            sending_stream = UNSET
        else:
            sending_stream = EmailLogsListResponseMessagesItemSendingStream(
                _sending_stream
            )

        domain_id = d.pop("domain_id", UNSET)

        def _parse_template_id(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        template_id = _parse_template_id(d.pop("template_id", UNSET))

        _template_variables = d.pop("template_variables", UNSET)
        template_variables: EmailLogsListResponseMessagesItemTemplateVariables | Unset
        if isinstance(_template_variables, Unset):
            template_variables = UNSET
        else:
            template_variables = (
                EmailLogsListResponseMessagesItemTemplateVariables.from_dict(
                    _template_variables
                )
            )

        opens_count = d.pop("opens_count", UNSET)

        clicks_count = d.pop("clicks_count", UNSET)

        email_logs_list_response_messages_item = cls(
            message_id=message_id,
            status=status,
            subject=subject,
            from_=from_,
            to=to,
            sent_at=sent_at,
            client_ip=client_ip,
            category=category,
            custom_variables=custom_variables,
            sending_stream=sending_stream,
            domain_id=domain_id,
            template_id=template_id,
            template_variables=template_variables,
            opens_count=opens_count,
            clicks_count=clicks_count,
        )

        email_logs_list_response_messages_item.additional_properties = d
        return email_logs_list_response_messages_item

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
