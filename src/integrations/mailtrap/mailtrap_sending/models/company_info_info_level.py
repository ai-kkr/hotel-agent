from enum import Enum


class CompanyInfoInfoLevel(str, Enum):
    BUSINESS = "business"
    INDIVIDUAL = "individual"

    def __str__(self) -> str:
        return str(self.value)
