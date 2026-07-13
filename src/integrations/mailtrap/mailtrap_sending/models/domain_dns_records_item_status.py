from enum import Enum


class DomainDnsRecordsItemStatus(str, Enum):
    FAIL = "fail"
    MISSING = "missing"
    NETWORK_ERROR = "network_error"
    PASS = "pass"
    SOFTFAIL = "softfail"
    UNCHECKED = "unchecked"

    def __str__(self) -> str:
        return str(self.value)
