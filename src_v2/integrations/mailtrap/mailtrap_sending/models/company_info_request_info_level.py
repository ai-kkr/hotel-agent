from enum import Enum


class CompanyInfoRequestInfoLevel(str, Enum):
    BUSINESS = "business"
    INDIVIDUAL = "individual"

    def __str__(self) -> str:
        return str(self.value)
