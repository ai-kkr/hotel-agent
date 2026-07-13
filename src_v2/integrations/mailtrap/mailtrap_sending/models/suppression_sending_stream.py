from enum import Enum


class SuppressionSendingStream(str, Enum):
    ANY = "any"
    BULK = "bulk"
    TRANSACTIONAL = "transactional"

    def __str__(self) -> str:
        return str(self.value)
