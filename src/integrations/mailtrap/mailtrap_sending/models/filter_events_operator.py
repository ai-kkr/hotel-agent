from enum import Enum


class FilterEventsOperator(str, Enum):
    INCLUDE_EVENT = "include_event"
    NOT_INCLUDE_EVENT = "not_include_event"

    def __str__(self) -> str:
        return str(self.value)
