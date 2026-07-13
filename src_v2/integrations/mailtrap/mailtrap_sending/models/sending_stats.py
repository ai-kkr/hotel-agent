from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SendingStats")


@_attrs_define
class SendingStats:
    """
    Attributes:
        delivery_count (int | Unset):  Example: 190.
        delivery_rate (float | Unset):  Example: 0.95.
        bounce_count (int | Unset):  Example: 10.
        bounce_rate (float | Unset):  Example: 0.05.
        open_count (int | Unset):  Example: 171.
        open_rate (float | Unset):  Example: 0.9.
        click_count (int | Unset):  Example: 133.
        click_rate (float | Unset):  Example: 0.7.
        spam_count (int | Unset):  Example: 3.
        spam_rate (float | Unset):  Example: 0.02.
    """

    delivery_count: int | Unset = UNSET
    delivery_rate: float | Unset = UNSET
    bounce_count: int | Unset = UNSET
    bounce_rate: float | Unset = UNSET
    open_count: int | Unset = UNSET
    open_rate: float | Unset = UNSET
    click_count: int | Unset = UNSET
    click_rate: float | Unset = UNSET
    spam_count: int | Unset = UNSET
    spam_rate: float | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        delivery_count = self.delivery_count

        delivery_rate = self.delivery_rate

        bounce_count = self.bounce_count

        bounce_rate = self.bounce_rate

        open_count = self.open_count

        open_rate = self.open_rate

        click_count = self.click_count

        click_rate = self.click_rate

        spam_count = self.spam_count

        spam_rate = self.spam_rate

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if delivery_count is not UNSET:
            field_dict["delivery_count"] = delivery_count
        if delivery_rate is not UNSET:
            field_dict["delivery_rate"] = delivery_rate
        if bounce_count is not UNSET:
            field_dict["bounce_count"] = bounce_count
        if bounce_rate is not UNSET:
            field_dict["bounce_rate"] = bounce_rate
        if open_count is not UNSET:
            field_dict["open_count"] = open_count
        if open_rate is not UNSET:
            field_dict["open_rate"] = open_rate
        if click_count is not UNSET:
            field_dict["click_count"] = click_count
        if click_rate is not UNSET:
            field_dict["click_rate"] = click_rate
        if spam_count is not UNSET:
            field_dict["spam_count"] = spam_count
        if spam_rate is not UNSET:
            field_dict["spam_rate"] = spam_rate

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        delivery_count = d.pop("delivery_count", UNSET)

        delivery_rate = d.pop("delivery_rate", UNSET)

        bounce_count = d.pop("bounce_count", UNSET)

        bounce_rate = d.pop("bounce_rate", UNSET)

        open_count = d.pop("open_count", UNSET)

        open_rate = d.pop("open_rate", UNSET)

        click_count = d.pop("click_count", UNSET)

        click_rate = d.pop("click_rate", UNSET)

        spam_count = d.pop("spam_count", UNSET)

        spam_rate = d.pop("spam_rate", UNSET)

        sending_stats = cls(
            delivery_count=delivery_count,
            delivery_rate=delivery_rate,
            bounce_count=bounce_count,
            bounce_rate=bounce_rate,
            open_count=open_count,
            open_rate=open_rate,
            click_count=click_count,
            click_rate=click_rate,
            spam_count=spam_count,
            spam_rate=spam_rate,
        )

        sending_stats.additional_properties = d
        return sending_stats

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
