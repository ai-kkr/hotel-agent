from enum import Enum


class WebhookPayloadFormat(str, Enum):
    JSON = "json"
    JSONLINES = "jsonlines"

    def __str__(self) -> str:
        return str(self.value)
