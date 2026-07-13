from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SendEmailErrorResponse")


@_attrs_define
class SendEmailErrorResponse:
    """Error responses from the sending API use `success: false` and an `errors` array of strings
    (unlike account APIs on `mailtrap.io`, which use `error` or a single `errors` string).

        Example:
            {'success': False, 'errors': ["'from' address is invalid"]}

        Attributes:
            success (bool | Unset):
            errors (list[str] | Unset):
    """

    success: bool | Unset = UNSET
    errors: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        success = self.success

        errors: list[str] | Unset = UNSET
        if not isinstance(self.errors, Unset):
            errors = self.errors

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if success is not UNSET:
            field_dict["success"] = success
        if errors is not UNSET:
            field_dict["errors"] = errors

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        success = d.pop("success", UNSET)

        errors = cast(list[str], d.pop("errors", UNSET))

        send_email_error_response = cls(
            success=success,
            errors=errors,
        )

        send_email_error_response.additional_properties = d
        return send_email_error_response

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
