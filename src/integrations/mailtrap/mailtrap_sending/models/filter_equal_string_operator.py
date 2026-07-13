from enum import Enum


class FilterEqualStringOperator(str, Enum):
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"

    def __str__(self) -> str:
        return str(self.value)
