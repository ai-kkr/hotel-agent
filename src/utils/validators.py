from typing import Annotated, Any

from pydantic import AfterValidator, BeforeValidator
from pydantic.networks import validate_email

_ABSENTL_SENTINELS = {"", "null", "none", "n/a", "na", "-", "--"}
__all__ = ["EmailAfter", "EmailOptional", "OptionalBefore"]


def _optional_before(value: Any) -> Any:
    """``mode="before"`` normalizer for optional fields: map sentinels/blanks to None."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in _ABSENTL_SENTINELS:
            return None
        return stripped
    return value


def _validate_email_after(v: str | None) -> str | None:
    """``mode="after"`` validator for Email fields: validate email if not None."""
    if v is None:
        return v
    return validate_email(v)[1]


OptionalBefore = BeforeValidator(_optional_before)
EmailAfter = AfterValidator(_validate_email_after)
type EmailOptional = Annotated[str | None, OptionalBefore, EmailAfter]
