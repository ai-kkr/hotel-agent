from enum import Enum


class MessageEventBounceEventType(str, Enum):
    BOUNCE = "bounce"
    SOFT_BOUNCE = "soft_bounce"

    def __str__(self) -> str:
        return str(self.value)
