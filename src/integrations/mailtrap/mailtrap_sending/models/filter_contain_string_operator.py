from enum import Enum


class FilterContainStringOperator(str, Enum):
    CONTAIN = "contain"
    NOT_CONTAIN = "not_contain"

    def __str__(self) -> str:
        return str(self.value)
