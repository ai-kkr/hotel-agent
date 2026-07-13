from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.create_suppression_body_sending_stream import (
    CreateSuppressionBodySendingStream,
)
from ..models.create_suppression_body_type import CreateSuppressionBodyType
from ..types import UNSET, Unset

T = TypeVar("T", bound="CreateSuppressionBody")


@_attrs_define
class CreateSuppressionBody:
    """
    Attributes:
        email (str): Email address to suppress Example: user@example.com.
        domain_id (int): ID of the domain to suppress this email for Example: 12345.
        sending_stream (CreateSuppressionBodySendingStream): The sending stream to suppress this email for Example:
            transactional.
        type_ (CreateSuppressionBodyType | Unset): Reason for the suppression. Defaults to "manual import" if omitted.
            Default: CreateSuppressionBodyType.MANUAL_IMPORT. Example: manual import.
    """

    email: str
    domain_id: int
    sending_stream: CreateSuppressionBodySendingStream
    type_: CreateSuppressionBodyType | Unset = CreateSuppressionBodyType.MANUAL_IMPORT
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        email = self.email

        domain_id = self.domain_id

        sending_stream = self.sending_stream.value

        type_: str | Unset = UNSET
        if not isinstance(self.type_, Unset):
            type_ = self.type_.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "email": email,
                "domain_id": domain_id,
                "sending_stream": sending_stream,
            }
        )
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        email = d.pop("email")

        domain_id = d.pop("domain_id")

        sending_stream = CreateSuppressionBodySendingStream(d.pop("sending_stream"))

        _type_ = d.pop("type", UNSET)
        type_: CreateSuppressionBodyType | Unset
        if isinstance(_type_, Unset):
            type_ = UNSET
        else:
            type_ = CreateSuppressionBodyType(_type_)

        create_suppression_body = cls(
            email=email,
            domain_id=domain_id,
            sending_stream=sending_stream,
            type_=type_,
        )

        create_suppression_body.additional_properties = d
        return create_suppression_body

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
