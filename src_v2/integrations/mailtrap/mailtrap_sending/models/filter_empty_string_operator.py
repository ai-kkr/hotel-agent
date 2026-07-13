from enum import Enum


class FilterEmptyStringOperator(str, Enum):
    EMPTY = "empty"
    NOT_EMPTY = "not_empty"

    def __str__(self) -> str:
        return str(self.value)
