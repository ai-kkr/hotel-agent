from enum import Enum


class DomainComplianceStatus(str, Enum):
    AWAITING_CARD_VERIFICATION = "awaiting_card_verification"
    AWAITING_QUESTIONNAIRE = "awaiting_questionnaire"
    COMPLIANT = "compliant"
    DEMO = "demo"
    DEMO_EXHAUSTED = "demo_exhausted"
    MISSING_COMPANY_INFO = "missing_company_info"
    NON_COMPLIANT = "non_compliant"
    SUSPENDED = "suspended"
    UNDER_REVIEW = "under_review"
    UNVERIFIED_DNS = "unverified_dns"

    def __str__(self) -> str:
        return str(self.value)
