from enum import Enum


class CreateWebhookBodyWebhookEventTypesItem(str, Enum):
    BOUNCE = "bounce"
    CLICK = "click"
    DELIVERY = "delivery"
    OPEN = "open"
    REJECT = "reject"
    SOFT_BOUNCE = "soft_bounce"
    SPAM_COMPLAINT = "spam_complaint"
    SUSPENSION = "suspension"
    UNSUBSCRIBE = "unsubscribe"

    def __str__(self) -> str:
        return str(self.value)
