from enum import Enum


class CreateSuppressionBodyType(str, Enum):
    HARD_BOUNCE = "hard bounce"
    MANUAL_IMPORT = "manual import"
    SPAM_COMPLAINT = "spam complaint"
    UNSUBSCRIPTION = "unsubscription"

    def __str__(self) -> str:
        return str(self.value)
