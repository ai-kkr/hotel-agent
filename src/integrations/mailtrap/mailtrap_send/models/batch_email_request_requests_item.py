from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.address import Address
    from ..models.email_attachments_attachments_item import (
        EmailAttachmentsAttachmentsItem,
    )
    from ..models.email_custom_variables_custom_variables import (
        EmailCustomVariablesCustomVariables,
    )
    from ..models.email_sending_headers_headers import EmailSendingHeadersHeaders
    from ..models.template_variables_template_variables import (
        TemplateVariablesTemplateVariables,
    )


T = TypeVar("T", bound="BatchEmailRequestRequestsItem")


@_attrs_define
class BatchEmailRequestRequestsItem:
    """
    Attributes:
        from_ (Address | Unset):
        to (list[Address] | Unset):
        cc (list[Address] | Unset):
        bcc (list[Address] | Unset):
        reply_to (Address | Unset):
        subject (str | Unset):  Example: Your Order Confirmation.
        text (str | Unset):  Example: Thank you for your order!.
        html (str | Unset):  Example: <h1>Thank you for your order!</h1>.
        attachments (list[EmailAttachmentsAttachmentsItem] | Unset):
        headers (EmailSendingHeadersHeaders | Unset):  Example: {'X-Message-Source': 'api.example.com', 'X-Campaign-ID':
            'CAMP-123'}.
        category (str | Unset):  Example: transactional.
        custom_variables (EmailCustomVariablesCustomVariables | Unset):  Example: {'user_id': '12345', 'order_id':
            'ORD-789'}.
        template_uuid (UUID | Unset): Email template UUID Example: b81aabcd-1a1e-41cf-91b6-eca0254b3d96.
        template_variables (TemplateVariablesTemplateVariables | Unset): Template variable values Example: {'user_name':
            'John Doe', 'order_number': '12345'}.
    """

    from_: Address | Unset = UNSET
    to: list[Address] | Unset = UNSET
    cc: list[Address] | Unset = UNSET
    bcc: list[Address] | Unset = UNSET
    reply_to: Address | Unset = UNSET
    subject: str | Unset = UNSET
    text: str | Unset = UNSET
    html: str | Unset = UNSET
    attachments: list[EmailAttachmentsAttachmentsItem] | Unset = UNSET
    headers: EmailSendingHeadersHeaders | Unset = UNSET
    category: str | Unset = UNSET
    custom_variables: EmailCustomVariablesCustomVariables | Unset = UNSET
    template_uuid: UUID | Unset = UNSET
    template_variables: TemplateVariablesTemplateVariables | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from_: dict[str, Any] | Unset = UNSET
        if not isinstance(self.from_, Unset):
            from_ = self.from_.to_dict()

        to: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.to, Unset):
            to = []
            for to_item_data in self.to:
                to_item = to_item_data.to_dict()
                to.append(to_item)

        cc: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.cc, Unset):
            cc = []
            for cc_item_data in self.cc:
                cc_item = cc_item_data.to_dict()
                cc.append(cc_item)

        bcc: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.bcc, Unset):
            bcc = []
            for bcc_item_data in self.bcc:
                bcc_item = bcc_item_data.to_dict()
                bcc.append(bcc_item)

        reply_to: dict[str, Any] | Unset = UNSET
        if not isinstance(self.reply_to, Unset):
            reply_to = self.reply_to.to_dict()

        subject = self.subject

        text = self.text

        html = self.html

        attachments: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.attachments, Unset):
            attachments = []
            for attachments_item_data in self.attachments:
                attachments_item = attachments_item_data.to_dict()
                attachments.append(attachments_item)

        headers: dict[str, Any] | Unset = UNSET
        if not isinstance(self.headers, Unset):
            headers = self.headers.to_dict()

        category = self.category

        custom_variables: dict[str, Any] | Unset = UNSET
        if not isinstance(self.custom_variables, Unset):
            custom_variables = self.custom_variables.to_dict()

        template_uuid: str | Unset = UNSET
        if not isinstance(self.template_uuid, Unset):
            template_uuid = str(self.template_uuid)

        template_variables: dict[str, Any] | Unset = UNSET
        if not isinstance(self.template_variables, Unset):
            template_variables = self.template_variables.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if from_ is not UNSET:
            field_dict["from"] = from_
        if to is not UNSET:
            field_dict["to"] = to
        if cc is not UNSET:
            field_dict["cc"] = cc
        if bcc is not UNSET:
            field_dict["bcc"] = bcc
        if reply_to is not UNSET:
            field_dict["reply_to"] = reply_to
        if subject is not UNSET:
            field_dict["subject"] = subject
        if text is not UNSET:
            field_dict["text"] = text
        if html is not UNSET:
            field_dict["html"] = html
        if attachments is not UNSET:
            field_dict["attachments"] = attachments
        if headers is not UNSET:
            field_dict["headers"] = headers
        if category is not UNSET:
            field_dict["category"] = category
        if custom_variables is not UNSET:
            field_dict["custom_variables"] = custom_variables
        if template_uuid is not UNSET:
            field_dict["template_uuid"] = template_uuid
        if template_variables is not UNSET:
            field_dict["template_variables"] = template_variables

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.address import Address
        from ..models.email_attachments_attachments_item import (
            EmailAttachmentsAttachmentsItem,
        )
        from ..models.email_custom_variables_custom_variables import (
            EmailCustomVariablesCustomVariables,
        )
        from ..models.email_sending_headers_headers import EmailSendingHeadersHeaders
        from ..models.template_variables_template_variables import (
            TemplateVariablesTemplateVariables,
        )

        d = dict(src_dict)
        _from_ = d.pop("from", UNSET)
        from_: Address | Unset
        if isinstance(_from_, Unset):
            from_ = UNSET
        else:
            from_ = Address.from_dict(_from_)

        _to = d.pop("to", UNSET)
        to: list[Address] | Unset = UNSET
        if _to is not UNSET:
            to = []
            for to_item_data in _to:
                to_item = Address.from_dict(to_item_data)

                to.append(to_item)

        _cc = d.pop("cc", UNSET)
        cc: list[Address] | Unset = UNSET
        if _cc is not UNSET:
            cc = []
            for cc_item_data in _cc:
                cc_item = Address.from_dict(cc_item_data)

                cc.append(cc_item)

        _bcc = d.pop("bcc", UNSET)
        bcc: list[Address] | Unset = UNSET
        if _bcc is not UNSET:
            bcc = []
            for bcc_item_data in _bcc:
                bcc_item = Address.from_dict(bcc_item_data)

                bcc.append(bcc_item)

        _reply_to = d.pop("reply_to", UNSET)
        reply_to: Address | Unset
        if isinstance(_reply_to, Unset):
            reply_to = UNSET
        else:
            reply_to = Address.from_dict(_reply_to)

        subject = d.pop("subject", UNSET)

        text = d.pop("text", UNSET)

        html = d.pop("html", UNSET)

        _attachments = d.pop("attachments", UNSET)
        attachments: list[EmailAttachmentsAttachmentsItem] | Unset = UNSET
        if _attachments is not UNSET:
            attachments = []
            for attachments_item_data in _attachments:
                attachments_item = EmailAttachmentsAttachmentsItem.from_dict(
                    attachments_item_data
                )

                attachments.append(attachments_item)

        _headers = d.pop("headers", UNSET)
        headers: EmailSendingHeadersHeaders | Unset
        if isinstance(_headers, Unset):
            headers = UNSET
        else:
            headers = EmailSendingHeadersHeaders.from_dict(_headers)

        category = d.pop("category", UNSET)

        _custom_variables = d.pop("custom_variables", UNSET)
        custom_variables: EmailCustomVariablesCustomVariables | Unset
        if isinstance(_custom_variables, Unset):
            custom_variables = UNSET
        else:
            custom_variables = EmailCustomVariablesCustomVariables.from_dict(
                _custom_variables
            )

        _template_uuid = d.pop("template_uuid", UNSET)
        template_uuid: UUID | Unset
        if isinstance(_template_uuid, Unset):
            template_uuid = UNSET
        else:
            template_uuid = UUID(_template_uuid)

        _template_variables = d.pop("template_variables", UNSET)
        template_variables: TemplateVariablesTemplateVariables | Unset
        if isinstance(_template_variables, Unset):
            template_variables = UNSET
        else:
            template_variables = TemplateVariablesTemplateVariables.from_dict(
                _template_variables
            )

        batch_email_request_requests_item = cls(
            from_=from_,
            to=to,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            subject=subject,
            text=text,
            html=html,
            attachments=attachments,
            headers=headers,
            category=category,
            custom_variables=custom_variables,
            template_uuid=template_uuid,
            template_variables=template_variables,
        )

        batch_email_request_requests_item.additional_properties = d
        return batch_email_request_requests_item

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
