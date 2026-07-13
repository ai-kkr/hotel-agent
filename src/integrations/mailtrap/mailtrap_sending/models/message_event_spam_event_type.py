from enum import Enum


class MessageEventSpamEventType(str, Enum):
    SPAM = "spam"

    def __str__(self) -> str:
        return str(self.value)
