from enum import Enum


class GetAccountSendingStatsByDateSendingStreamsItem(str, Enum):
    BULK = "bulk"
    TRANSACTIONAL = "transactional"

    def __str__(self) -> str:
        return str(self.value)
