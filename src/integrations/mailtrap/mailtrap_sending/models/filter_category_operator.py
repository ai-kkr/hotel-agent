from enum import Enum


class FilterCategoryOperator(str, Enum):
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"

    def __str__(self) -> str:
        return str(self.value)
