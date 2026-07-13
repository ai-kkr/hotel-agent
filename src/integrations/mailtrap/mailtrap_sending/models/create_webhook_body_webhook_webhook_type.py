from enum import Enum


class CreateWebhookBodyWebhookWebhookType(str, Enum):
    AUDIT_LOG = "audit_log"
    CAMPAIGNS = "campaigns"
    EMAIL_SENDING = "email_sending"
    INBOUND_RECEIVING = "inbound_receiving"

    def __str__(self) -> str:
        return str(self.value)
