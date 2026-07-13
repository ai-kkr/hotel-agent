from enum import Enum


class MessageEventUnsubscribeEventType(str, Enum):
    UNSUBSCRIBE = "unsubscribe"

    def __str__(self) -> str:
        return str(self.value)
