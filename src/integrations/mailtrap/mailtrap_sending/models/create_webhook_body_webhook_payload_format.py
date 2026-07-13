from enum import Enum


class CreateWebhookBodyWebhookPayloadFormat(str, Enum):
    JSON = "json"
    JSONLINES = "jsonlines"

    def __str__(self) -> str:
        return str(self.value)
