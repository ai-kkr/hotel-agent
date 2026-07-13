from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.create_webhook_body_webhook import CreateWebhookBodyWebhook


T = TypeVar("T", bound="CreateWebhookBody")


@_attrs_define
class CreateWebhookBody:
    """
    Attributes:
        webhook (CreateWebhookBodyWebhook):
    """

    webhook: CreateWebhookBodyWebhook
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        webhook = self.webhook.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "webhook": webhook,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.create_webhook_body_webhook import CreateWebhookBodyWebhook

        d = dict(src_dict)
        webhook = CreateWebhookBodyWebhook.from_dict(d.pop("webhook"))

        create_webhook_body = cls(
            webhook=webhook,
        )

        create_webhook_body.additional_properties = d
        return create_webhook_body

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
