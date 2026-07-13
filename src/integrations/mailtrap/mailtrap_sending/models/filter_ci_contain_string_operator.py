from enum import Enum


class FilterCiContainStringOperator(str, Enum):
    CI_CONTAIN = "ci_contain"
    CI_NOT_CONTAIN = "ci_not_contain"

    def __str__(self) -> str:
        return str(self.value)
