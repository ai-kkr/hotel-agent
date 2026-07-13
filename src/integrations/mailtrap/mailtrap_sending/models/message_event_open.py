from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.message_event_open_event_type import MessageEventOpenEventType

if TYPE_CHECKING:
    from ..models.event_details_open import EventDetailsOpen


T = TypeVar("T", bound="MessageEventOpen")


@_attrs_define
class MessageEventOpen:
    """
    Attributes:
        event_type (MessageEventOpenEventType):
        created_at (datetime.datetime):
        details (EventDetailsOpen): For event_type = open Example: {'web_ip_address': '198.51.100.50'}.
    """

    event_type: MessageEventOpenEventType
    created_at: datetime.datetime
    details: EventDetailsOpen
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        event_type = self.event_type.value

        created_at = self.created_at.isoformat()

        details = self.details.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "event_type": event_type,
                "created_at": created_at,
                "details": details,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.event_details_open import EventDetailsOpen

        d = dict(src_dict)
        event_type = MessageEventOpenEventType(d.pop("event_type"))

        created_at = datetime.datetime.fromisoformat(d.pop("created_at"))

        details = EventDetailsOpen.from_dict(d.pop("details"))

        message_event_open = cls(
            event_type=event_type,
            created_at=created_at,
            details=details,
        )

        message_event_open.additional_properties = d
        return message_event_open

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
