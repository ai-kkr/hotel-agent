from enum import Enum


class FilterStatusValueType0(str, Enum):
    DELIVERED = "delivered"
    ENQUEUED = "enqueued"
    NOT_DELIVERED = "not_delivered"
    OPTED_OUT = "opted_out"

    def __str__(self) -> str:
        return str(self.value)
