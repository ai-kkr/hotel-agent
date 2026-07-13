"""Contains all the data models used in inputs/outputs"""

from .address import Address
from .batch_email_request import BatchEmailRequest
from .batch_email_request_base import BatchEmailRequestBase
from .batch_email_request_requests_item import BatchEmailRequestRequestsItem
from .batch_sent_response import BatchSentResponse
from .batch_sent_response_responses_item import BatchSentResponseResponsesItem
from .email_attachments import EmailAttachments
from .email_attachments_attachments_item import EmailAttachmentsAttachmentsItem
from .email_attachments_attachments_item_disposition import (
    EmailAttachmentsAttachmentsItemDisposition,
)
from .email_category import EmailCategory
from .email_custom_variables import EmailCustomVariables
from .email_custom_variables_custom_variables import EmailCustomVariablesCustomVariables
from .email_html import EmailHtml
from .email_html_required import EmailHtmlRequired
from .email_recipients import EmailRecipients
from .email_reply_to import EmailReplyTo
from .email_sender import EmailSender
from .email_sender_required import EmailSenderRequired
from .email_sending_headers import EmailSendingHeaders
from .email_sending_headers_headers import EmailSendingHeadersHeaders
from .email_subject import EmailSubject
from .email_subject_required import EmailSubjectRequired
from .email_text import EmailText
from .email_text_required import EmailTextRequired
from .from_template import FromTemplate
from .html_only import HTMLOnly
from .send_email_error_response import SendEmailErrorResponse
from .sent_response import SentResponse
from .template_uuid import TemplateUuid
from .template_uuid_required import TemplateUuidRequired
from .template_variables import TemplateVariables
from .template_variables_template_variables import TemplateVariablesTemplateVariables
from .text_and_html import TextAndHTML
from .text_only import TextOnly

__all__ = (
    "Address",
    "BatchEmailRequest",
    "BatchEmailRequestBase",
    "BatchEmailRequestRequestsItem",
    "BatchSentResponse",
    "BatchSentResponseResponsesItem",
    "EmailAttachments",
    "EmailAttachmentsAttachmentsItem",
    "EmailAttachmentsAttachmentsItemDisposition",
    "EmailCategory",
    "EmailCustomVariables",
    "EmailCustomVariablesCustomVariables",
    "EmailHtml",
    "EmailHtmlRequired",
    "EmailRecipients",
    "EmailReplyTo",
    "EmailSender",
    "EmailSenderRequired",
    "EmailSendingHeaders",
    "EmailSendingHeadersHeaders",
    "EmailSubject",
    "EmailSubjectRequired",
    "EmailText",
    "EmailTextRequired",
    "FromTemplate",
    "HTMLOnly",
    "SendEmailErrorResponse",
    "SentResponse",
    "TemplateUuid",
    "TemplateUuidRequired",
    "TemplateVariables",
    "TemplateVariablesTemplateVariables",
    "TextAndHTML",
    "TextOnly",
)
