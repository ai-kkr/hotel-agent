from enum import Enum


class CompanyInfoUpdateRequestInfoLevel(str, Enum):
    BUSINESS = "business"
    INDIVIDUAL = "individual"

    def __str__(self) -> str:
        return str(self.value)
