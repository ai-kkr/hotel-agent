from enum import Enum


class FilterStatusOperator(str, Enum):
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"

    def __str__(self) -> str:
        return str(self.value)
