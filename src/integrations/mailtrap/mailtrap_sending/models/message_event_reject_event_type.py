from enum import Enum


class MessageEventRejectEventType(str, Enum):
    REJECT = "reject"
    SUSPENSION = "suspension"

    def __str__(self) -> str:
        return str(self.value)
