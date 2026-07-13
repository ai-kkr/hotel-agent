from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.sending_stats import SendingStats


T = TypeVar("T", bound="GetAccountSendingStatsByCategoriesResponse200Item")


@_attrs_define
class GetAccountSendingStatsByCategoriesResponse200Item:
    """
    Attributes:
        category (str | Unset):  Example: Welcome Email.
        stats (SendingStats | Unset):
    """

    category: str | Unset = UNSET
    stats: SendingStats | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        category = self.category

        stats: dict[str, Any] | Unset = UNSET
        if not isinstance(self.stats, Unset):
            stats = self.stats.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if category is not UNSET:
            field_dict["category"] = category
        if stats is not UNSET:
            field_dict["stats"] = stats

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.sending_stats import SendingStats

        d = dict(src_dict)
        category = d.pop("category", UNSET)

        _stats = d.pop("stats", UNSET)
        stats: SendingStats | Unset
        if isinstance(_stats, Unset):
            stats = UNSET
        else:
            stats = SendingStats.from_dict(_stats)

        get_account_sending_stats_by_categories_response_200_item = cls(
            category=category,
            stats=stats,
        )

        get_account_sending_stats_by_categories_response_200_item.additional_properties = d
        return get_account_sending_stats_by_categories_response_200_item

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
