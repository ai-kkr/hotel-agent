from enum import Enum


class MessageEventClickEventType(str, Enum):
    CLICK = "click"

    def __str__(self) -> str:
        return str(self.value)
