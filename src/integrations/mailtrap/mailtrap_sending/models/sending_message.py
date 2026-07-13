from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.sending_message_sending_stream import SendingMessageSendingStream
from ..models.sending_message_status import SendingMessageStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.message_event_bounce import MessageEventBounce
    from ..models.message_event_click import MessageEventClick
    from ..models.message_event_delivery import MessageEventDelivery
    from ..models.message_event_open import MessageEventOpen
    from ..models.message_event_reject import MessageEventReject
    from ..models.message_event_spam import MessageEventSpam
    from ..models.message_event_unsubscribe import MessageEventUnsubscribe
    from ..models.sending_message_custom_variables import SendingMessageCustomVariables
    from ..models.sending_message_template_variables import (
        SendingMessageTemplateVariables,
    )


T = TypeVar("T", bound="SendingMessage")


@_attrs_define
class SendingMessage:
    """
    Example:
        {'message_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'status': 'delivered', 'subject': 'Welcome to our
            service', 'from': 'sender@example.com', 'to': 'recipient@example.com', 'sent_at': '2025-01-15T10:30:00Z',
            'client_ip': '203.0.113.42', 'category': 'Welcome Email', 'custom_variables': {}, 'sending_stream':
            'transactional', 'domain_id': 3938, 'template_id': 100, 'template_variables': {}, 'opens_count': 2,
            'clicks_count': 1, 'raw_message_url': 'https://storage.example.com/signed/eml/a1b2c3d4-e5f6-7890-abcd-
            ef1234567890?token=...', 'events': [{'event_type': 'click', 'created_at': '2025-01-15T10:35:00Z', 'details':
            {'click_url': 'https://example.com/track/click/abc123', 'web_ip_address': '198.51.100.50'}}, {'event_type':
            'spam', 'created_at': '2025-01-15T10:40:00Z', 'details': {'spam_feedback_type': 'abuse'}}]}

    Attributes:
        message_id (UUID | Unset):
        status (SendingMessageStatus | Unset):
        subject (None | str | Unset):
        from_ (str | Unset):
        to (str | Unset):
        sent_at (datetime.datetime | Unset):
        client_ip (None | str | Unset):
        category (None | str | Unset):
        custom_variables (SendingMessageCustomVariables | Unset):
        sending_stream (SendingMessageSendingStream | Unset):
        domain_id (int | Unset):
        template_id (int | None | Unset):
        template_variables (SendingMessageTemplateVariables | Unset):
        opens_count (int | Unset):
        clicks_count (int | Unset):
        raw_message_url (str | Unset): Signed URL to download raw .eml message (temporary).
        events (list[MessageEventBounce | MessageEventClick | MessageEventDelivery | MessageEventOpen |
            MessageEventReject | MessageEventSpam | MessageEventUnsubscribe] | Unset):
    """

    message_id: UUID | Unset = UNSET
    status: SendingMessageStatus | Unset = UNSET
    subject: None | str | Unset = UNSET
    from_: str | Unset = UNSET
    to: str | Unset = UNSET
    sent_at: datetime.datetime | Unset = UNSET
    client_ip: None | str | Unset = UNSET
    category: None | str | Unset = UNSET
    custom_variables: SendingMessageCustomVariables | Unset = UNSET
    sending_stream: SendingMessageSendingStream | Unset = UNSET
    domain_id: int | Unset = UNSET
    template_id: int | None | Unset = UNSET
    template_variables: SendingMessageTemplateVariables | Unset = UNSET
    opens_count: int | Unset = UNSET
    clicks_count: int | Unset = UNSET
    raw_message_url: str | Unset = UNSET
    events: (
        list[
            MessageEventBounce
            | MessageEventClick
            | MessageEventDelivery
            | MessageEventOpen
            | MessageEventReject
            | MessageEventSpam
            | MessageEventUnsubscribe
        ]
        | Unset
    ) = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.message_event_bounce import MessageEventBounce
        from ..models.message_event_click import MessageEventClick
        from ..models.message_event_delivery import MessageEventDelivery
        from ..models.message_event_open import MessageEventOpen
        from ..models.message_event_spam import MessageEventSpam
        from ..models.message_event_unsubscribe import MessageEventUnsubscribe

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

        raw_message_url = self.raw_message_url

        events: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.events, Unset):
            events = []
            for events_item_data in self.events:
                events_item: dict[str, Any]
                if isinstance(events_item_data, MessageEventDelivery) or isinstance(events_item_data, MessageEventOpen) or isinstance(events_item_data, MessageEventClick) or isinstance(events_item_data, MessageEventBounce) or isinstance(events_item_data, MessageEventSpam) or isinstance(events_item_data, MessageEventUnsubscribe):
                    events_item = events_item_data.to_dict()
                else:
                    events_item = events_item_data.to_dict()

                events.append(events_item)

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
        if raw_message_url is not UNSET:
            field_dict["raw_message_url"] = raw_message_url
        if events is not UNSET:
            field_dict["events"] = events

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.message_event_bounce import MessageEventBounce
        from ..models.message_event_click import MessageEventClick
        from ..models.message_event_delivery import MessageEventDelivery
        from ..models.message_event_open import MessageEventOpen
        from ..models.message_event_reject import MessageEventReject
        from ..models.message_event_spam import MessageEventSpam
        from ..models.message_event_unsubscribe import MessageEventUnsubscribe
        from ..models.sending_message_custom_variables import (
            SendingMessageCustomVariables,
        )
        from ..models.sending_message_template_variables import (
            SendingMessageTemplateVariables,
        )

        d = dict(src_dict)
        _message_id = d.pop("message_id", UNSET)
        message_id: UUID | Unset
        if isinstance(_message_id, Unset):
            message_id = UNSET
        else:
            message_id = UUID(_message_id)

        _status = d.pop("status", UNSET)
        status: SendingMessageStatus | Unset
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = SendingMessageStatus(_status)

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
        custom_variables: SendingMessageCustomVariables | Unset
        if isinstance(_custom_variables, Unset):
            custom_variables = UNSET
        else:
            custom_variables = SendingMessageCustomVariables.from_dict(
                _custom_variables
            )

        _sending_stream = d.pop("sending_stream", UNSET)
        sending_stream: SendingMessageSendingStream | Unset
        if isinstance(_sending_stream, Unset):
            sending_stream = UNSET
        else:
            sending_stream = SendingMessageSendingStream(_sending_stream)

        domain_id = d.pop("domain_id", UNSET)

        def _parse_template_id(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        template_id = _parse_template_id(d.pop("template_id", UNSET))

        _template_variables = d.pop("template_variables", UNSET)
        template_variables: SendingMessageTemplateVariables | Unset
        if isinstance(_template_variables, Unset):
            template_variables = UNSET
        else:
            template_variables = SendingMessageTemplateVariables.from_dict(
                _template_variables
            )

        opens_count = d.pop("opens_count", UNSET)

        clicks_count = d.pop("clicks_count", UNSET)

        raw_message_url = d.pop("raw_message_url", UNSET)

        _events = d.pop("events", UNSET)
        events: (
            list[
                MessageEventBounce
                | MessageEventClick
                | MessageEventDelivery
                | MessageEventOpen
                | MessageEventReject
                | MessageEventSpam
                | MessageEventUnsubscribe
            ]
            | Unset
        ) = UNSET
        if _events is not UNSET:
            events = []
            for events_item_data in _events:

                def _parse_events_item(
                    data: object,
                ) -> (
                    MessageEventBounce
                    | MessageEventClick
                    | MessageEventDelivery
                    | MessageEventOpen
                    | MessageEventReject
                    | MessageEventSpam
                    | MessageEventUnsubscribe
                ):
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        componentsschemas_message_event_type_0 = (
                            MessageEventDelivery.from_dict(data)
                        )

                        return componentsschemas_message_event_type_0
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        componentsschemas_message_event_type_1 = (
                            MessageEventOpen.from_dict(data)
                        )

                        return componentsschemas_message_event_type_1
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        componentsschemas_message_event_type_2 = (
                            MessageEventClick.from_dict(data)
                        )

                        return componentsschemas_message_event_type_2
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        componentsschemas_message_event_type_3 = (
                            MessageEventBounce.from_dict(data)
                        )

                        return componentsschemas_message_event_type_3
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        componentsschemas_message_event_type_4 = (
                            MessageEventSpam.from_dict(data)
                        )

                        return componentsschemas_message_event_type_4
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        componentsschemas_message_event_type_5 = (
                            MessageEventUnsubscribe.from_dict(data)
                        )

                        return componentsschemas_message_event_type_5
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_message_event_type_6 = (
                        MessageEventReject.from_dict(data)
                    )

                    return componentsschemas_message_event_type_6

                events_item = _parse_events_item(events_item_data)

                events.append(events_item)

        sending_message = cls(
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
            raw_message_url=raw_message_url,
            events=events,
        )

        sending_message.additional_properties = d
        return sending_message

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
