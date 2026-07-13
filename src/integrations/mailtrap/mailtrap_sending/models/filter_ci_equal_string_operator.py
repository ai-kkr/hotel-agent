from enum import Enum


class FilterCiEqualStringOperator(str, Enum):
    CI_EQUAL = "ci_equal"
    CI_NOT_EQUAL = "ci_not_equal"

    def __str__(self) -> str:
        return str(self.value)
