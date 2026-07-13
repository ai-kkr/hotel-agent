from enum import Enum


class FilterEventsValueType0(str, Enum):
    BOUNCE = "bounce"
    CLICK = "click"
    DELIVERY = "delivery"
    OPEN = "open"
    REJECT = "reject"
    SOFT_BOUNCE = "soft_bounce"
    SPAM = "spam"
    SUSPENSION = "suspension"
    UNSUBSCRIBE = "unsubscribe"

    def __str__(self) -> str:
        return str(self.value)
