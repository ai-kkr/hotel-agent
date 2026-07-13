from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="EventDetailsSpam")


@_attrs_define
class EventDetailsSpam:
    """For event_type = spam

    Example:
        {'spam_feedback_type': 'abuse'}

    Attributes:
        spam_feedback_type (None | str | Unset):
    """

    spam_feedback_type: None | str | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        spam_feedback_type: None | str | Unset
        if isinstance(self.spam_feedback_type, Unset):
            spam_feedback_type = UNSET
        else:
            spam_feedback_type = self.spam_feedback_type

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if spam_feedback_type is not UNSET:
            field_dict["spam_feedback_type"] = spam_feedback_type

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_spam_feedback_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        spam_feedback_type = _parse_spam_feedback_type(
            d.pop("spam_feedback_type", UNSET)
        )

        event_details_spam = cls(
            spam_feedback_type=spam_feedback_type,
        )

        return event_details_spam
