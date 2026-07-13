from enum import Enum


class WebhookSendingStreamType3Type1(str, Enum):
    BULK = "bulk"
    TRANSACTIONAL = "transactional"

    def __str__(self) -> str:
        return str(self.value)
