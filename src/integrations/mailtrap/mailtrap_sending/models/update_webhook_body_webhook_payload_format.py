from enum import Enum


class UpdateWebhookBodyWebhookPayloadFormat(str, Enum):
    JSON = "json"
    JSONLINES = "jsonlines"

    def __str__(self) -> str:
        return str(self.value)
