from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.email_logs_list_response_messages_item import (
        EmailLogsListResponseMessagesItem,
    )


T = TypeVar("T", bound="EmailLogsListResponse")


@_attrs_define
class EmailLogsListResponse:
    """
    Example:
        {'messages': [{'message_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'status': 'delivered', 'subject': 'Welcome
            to our service', 'from': 'sender@example.com', 'to': 'recipient@example.com', 'sent_at': '2025-01-15T10:30:00Z',
            'client_ip': '203.0.113.42', 'category': 'Welcome Email', 'custom_variables': {}, 'sending_stream':
            'transactional', 'domain_id': 3938, 'template_id': 100, 'template_variables': {}, 'opens_count': 2,
            'clicks_count': 1}, {'message_id': 'b2c3d4e5-f6a7-8901-bcde-f12345678901', 'status': 'delivered', 'subject':
            'Your order confirmation', 'from': 'orders@example.com', 'to': 'customer@example.com', 'sent_at':
            '2025-01-15T11:00:00Z', 'client_ip': None, 'category': 'Order Confirmation', 'custom_variables': {'order_id':
            '12345'}, 'sending_stream': 'transactional', 'domain_id': 3938, 'template_id': None, 'template_variables': {},
            'opens_count': 0, 'clicks_count': 0}], 'total_count': 150, 'next_page_cursor':
            'b2c3d4e5-f6a7-8901-bcde-f12345678901'}

    Attributes:
        messages (list[EmailLogsListResponseMessagesItem]):
        total_count (int): Total number of messages matching the filters (before pagination).
        next_page_cursor (None | UUID): Message UUID to use as search_after for the next page. Null if no more pages.
    """

    messages: list[EmailLogsListResponseMessagesItem]
    total_count: int
    next_page_cursor: None | UUID
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        messages = []
        for messages_item_data in self.messages:
            messages_item = messages_item_data.to_dict()
            messages.append(messages_item)

        total_count = self.total_count

        next_page_cursor: None | str
        if isinstance(self.next_page_cursor, UUID):
            next_page_cursor = str(self.next_page_cursor)
        else:
            next_page_cursor = self.next_page_cursor

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "messages": messages,
                "total_count": total_count,
                "next_page_cursor": next_page_cursor,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.email_logs_list_response_messages_item import (
            EmailLogsListResponseMessagesItem,
        )

        d = dict(src_dict)
        messages = []
        _messages = d.pop("messages")
        for messages_item_data in _messages:
            messages_item = EmailLogsListResponseMessagesItem.from_dict(
                messages_item_data
            )

            messages.append(messages_item)

        total_count = d.pop("total_count")

        def _parse_next_page_cursor(data: object) -> None | UUID:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                next_page_cursor_type_0 = UUID(data)

                return next_page_cursor_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | UUID, data)

        next_page_cursor = _parse_next_page_cursor(d.pop("next_page_cursor"))

        email_logs_list_response = cls(
            messages=messages,
            total_count=total_count,
            next_page_cursor=next_page_cursor,
        )

        email_logs_list_response.additional_properties = d
        return email_logs_list_response

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
