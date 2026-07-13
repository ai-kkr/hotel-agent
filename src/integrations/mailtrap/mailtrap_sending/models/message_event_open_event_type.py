from enum import Enum


class MessageEventOpenEventType(str, Enum):
    OPEN = "open"

    def __str__(self) -> str:
        return str(self.value)
