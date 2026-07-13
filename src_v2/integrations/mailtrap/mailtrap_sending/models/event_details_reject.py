from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="EventDetailsReject")


@_attrs_define
class EventDetailsReject:
    """For event_type = suspension or reject

    Example:
        {'reject_reason': 'Policy rejection'}

    Attributes:
        reject_reason (None | str | Unset):
    """

    reject_reason: None | str | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        reject_reason: None | str | Unset
        if isinstance(self.reject_reason, Unset):
            reject_reason = UNSET
        else:
            reject_reason = self.reject_reason

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if reject_reason is not UNSET:
            field_dict["reject_reason"] = reject_reason

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_reject_reason(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        reject_reason = _parse_reject_reason(d.pop("reject_reason", UNSET))

        event_details_reject = cls(
            reject_reason=reject_reason,
        )

        return event_details_reject
