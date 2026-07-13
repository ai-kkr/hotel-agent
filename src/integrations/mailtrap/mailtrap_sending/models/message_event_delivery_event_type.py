from enum import Enum


class MessageEventDeliveryEventType(str, Enum):
    DELIVERY = "delivery"

    def __str__(self) -> str:
        return str(self.value)
