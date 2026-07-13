from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.message import Message


T = TypeVar("T", bound="MessagesListResponse")


@_attrs_define
class MessagesListResponse:
    """
    Attributes:
        data (list[Message]):
        total_count (int): Total number of messages within the retention window. Example: 1.
        last_id (None | str): Cursor for the next page. `null` when there are no more results.
    """

    data: list[Message]
    total_count: int
    last_id: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = []
        for data_item_data in self.data:
            data_item = data_item_data.to_dict()
            data.append(data_item)

        total_count = self.total_count

        last_id: None | str
        last_id = self.last_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "data": data,
                "total_count": total_count,
                "last_id": last_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.message import Message

        d = dict(src_dict)
        data = []
        _data = d.pop("data")
        for data_item_data in _data:
            data_item = Message.from_dict(data_item_data)

            data.append(data_item)

        total_count = d.pop("total_count")

        def _parse_last_id(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        last_id = _parse_last_id(d.pop("last_id"))

        messages_list_response = cls(
            data=data,
            total_count=total_count,
            last_id=last_id,
        )

        messages_list_response.additional_properties = d
        return messages_list_response

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
