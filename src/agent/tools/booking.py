"""Booking-domain tool: ``set_booking_info`` and the booking-field helpers."""

from typing import Literal, cast
from zoneinfo import ZoneInfo

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.types import Command

from src.logging import get_logger

from ..context import EmailContext
from ..exceptions import SelfCorrectionError
from ..state import EmailState
from ..types import MessageText
from ..utils import send_telegram_reply
from .utils import ack

__all__ = ["REQUIRED_BOOKING_FIELDS", "missing_booking_fields", "set_booking_info"]

log = get_logger(__name__)


def _validate_timezone(value: str | None, field: str) -> str | None:
    """Validate an IANA timezone name (e.g. ``Europe/Moscow``); ``None`` is a no-op.

    A bad name self-corrects (the agent is told the field and to ask the guest) rather than crashing
    the turn.
    """
    if value is None:
        return None
    try:
        ZoneInfo(value)
    except Exception as exc:  # ZoneInfoNotFoundError / KeyError on unknown names
        raise SelfCorrectionError(
            f"Неверный часовой пояс для {field}: {value!r}. Используй IANA-имя, например "
            "'Europe/Moscow', 'Asia/Shanghai', 'Europe/Istanbul'. Уточни у пользователя."
        ) from exc
    return value


#: Booking fields that ``send_wishes_to_hotel`` requires to be non-empty before it can send.
REQUIRED_BOOKING_FIELDS: tuple[str, ...] = (
    "hotel_name",
    "from_date",
    "to_date",
    "hotel_email",
    "guests",
    "hotel_language",
)

#: Russian labels for the booking fields, in display order.
_BOOKING_LABELS: tuple[tuple[str, str], ...] = (
    ("hotel_name", "Отель"),
    ("booking_ref", "Номер брони"),
    ("from_date", "Заезд"),
    ("to_date", "Выезд"),
    ("hotel_email", "Email отеля"),
    ("guests", "Гости"),
    ("hotel_language", "Язык письма"),
    ("home_timezone", "Часовой пояс дома"),
    ("trip_timezone", "Часовой пояс поездки"),
)

#: Map ``hotel_language`` code → human label for the booking summary.
_LANGUAGE_LABELS: dict[str, str] = {"ru": "Русский", "zh": "Китайский", "en": "Английский"}


def missing_booking_fields(state: EmailState) -> list[str]:
    """Names of required booking fields that are absent/empty in ``state``."""
    missing: list[str] = []
    for field in REQUIRED_BOOKING_FIELDS:
        value = state.get(field)
        if value is None or value == [] or value == "":
            missing.append(field)
    return missing


def _format_booking_summary(
    *,
    hotel_name: str | None,
    booking_ref: str | None,
    from_date: str | None,
    to_date: str | None,
    hotel_email: str | None,
    guests: list[str] | None,
    hotel_language: str | None,
    home_timezone: str | None,
    trip_timezone: str | None,
) -> MessageText | None:
    """Build a Russian markdown-list summary of the non-empty booking fields being set.

    Returns ``None`` when every field is empty (nothing to announce).
    """
    values: dict[str, object] = {
        "hotel_name": hotel_name,
        "booking_ref": booking_ref,
        "from_date": from_date,
        "to_date": to_date,
        "hotel_email": hotel_email,
        "guests": guests,
        "hotel_language": _LANGUAGE_LABELS.get(hotel_language, hotel_language)
        if hotel_language
        else None,
        "home_timezone": home_timezone,
        "trip_timezone": trip_timezone,
    }
    lines: list[str] = []
    for field, label in _BOOKING_LABELS:
        value = values[field]
        if value is None or value == "" or value == []:
            continue
        rendered = ", ".join(cast(list[str], value)) if isinstance(value, list) else str(value)
        lines.append(f"- {label}: {rendered}")
    if not lines:
        return None
    return MessageText(text="Записал данные брони:\n" + "\n".join(lines))


@tool
async def set_booking_info(
    runtime: ToolRuntime[EmailContext, EmailState],
    hotel_name: str | None = None,
    booking_ref: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    hotel_email: str | None = None,
    guests: list[str] | None = None,
    hotel_language: Literal["ru", "zh", "en"] | None = None,
    home_timezone: str | None = None,
    trip_timezone: str | None = None,
):
    """Record booking details as you learn them. Leave a field null (omit it) to keep it unchanged.

    Call this incrementally as you parse the forwarded confirmation or clarify details with the
    user. A null argument is a no-op (the existing value is kept via the ``booking_field``
    reducer). All listed fields must be filled before ``send_wishes_to_hotel``.

    ``home_timezone`` / ``trip_timezone`` are IANA names (e.g. ``Europe/Moscow``,
    ``Asia/Shanghai``) and anchor the times the guest gives to the scheduling tools: ``home`` is the
    guest's home zone, ``trip`` is the destination/hotel zone. Set them as soon as you know where the
    guest is and where they're going — scheduling a task is impossible before the relevant zone is set.

    Args:
        hotel_name: Hotel name.
        booking_ref: Booking reference / confirmation number, if the confirmation carries one.
            Optional — not every voucher has a code; leave null when absent.
        from_date: Check-in date (``YYYY-MM-DD``).
        to_date: Check-out date (``YYYY-MM-DD``).
        hotel_email: Hotel contact email.
        guests: Guest names/labels.
        hotel_language: Language for the letter to the hotel — ``ru`` (Russia), ``zh`` (China),
            ``en`` (any other country). Determine from the hotel's country.
        home_timezone: IANA timezone of the guest's home (e.g. ``Europe/Moscow``).
        trip_timezone: IANA timezone of the trip / hotel (e.g. ``Asia/Shanghai``).
    """
    home_timezone = _validate_timezone(home_timezone, "home_timezone")
    trip_timezone = _validate_timezone(trip_timezone, "trip_timezone")
    log.info(
        "tool.set_booking_info",
        hotel_name=hotel_name,
        booking_ref=booking_ref,
        from_date=from_date,
        to_date=to_date,
        hotel_email=hotel_email,
        guests=guests,
        hotel_language=hotel_language,
        home_timezone=home_timezone,
        trip_timezone=trip_timezone,
    )
    summary = _format_booking_summary(
        hotel_name=hotel_name,
        booking_ref=booking_ref,
        from_date=from_date,
        to_date=to_date,
        hotel_email=hotel_email,
        guests=guests,
        hotel_language=hotel_language,
        home_timezone=home_timezone,
        trip_timezone=trip_timezone,
    )
    if summary is not None:
        await send_telegram_reply(summary.text)
    return Command(
        update={
            "hotel_name": hotel_name,
            "booking_ref": booking_ref,
            "from_date": from_date,
            "to_date": to_date,
            "hotel_email": hotel_email,
            "guests": guests,
            "hotel_language": hotel_language,
            "home_timezone": home_timezone,
            "trip_timezone": trip_timezone,
            "messages": [ack(runtime)],
        }
    )
