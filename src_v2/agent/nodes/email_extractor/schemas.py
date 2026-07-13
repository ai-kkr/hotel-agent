"""Pydantic schemas produced by the email-extraction graph nodes."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from src_v2.utils.validators import EmailOptional, OptionalBefore

__all__ = ["ExtractedBookingSchema", "HotelLanguage", "UserIntentionSchema", "UserReplyClassification"]

#: Language the outgoing letter to the hotel should be written in, derived from the hotel's
#: country: Russian hotels → ``ru``, Chinese → ``zh``, every other foreign hotel → ``en``.
HotelLanguage = Literal["ru", "en", "zh"]


class ExtractedBookingSchema(BaseModel):
    """Structured extraction of a forwarded booking confirmation."""

    hotel_name: str = Field(description="Название отеля из письма или подтверждения брони")
    hotel_language: HotelLanguage = Field(
        description=(
            "Язык для письма в отель по стране отеля: "
            "`ru` — отель в России, `zh` — отель в Китае, "
            "`en` — любой другой иностранный отель. "
            "Страну определяй по названию отеля, локации, адресу, курорту из письма."
        )
    )
    hotel_email: EmailOptional | None = Field(default=None, description="Email отеля для связи")
    hotel_website: str | None = Field(default=None, description="Сайт отеля (URL), если указан")
    booking_ref: Annotated[str | None, OptionalBefore] = Field(
        default=None, description="Номер или код бронирования"
    )
    check_in: str | None = Field(default=None, description="Дата заезда в формате YYYY-MM-DD")  # type: ignore[assignment]
    check_out: str | None = Field(default=None, description="Дата выезда в формате YYYY-MM-DD")  # type: ignore[assignment]
    guests: list[str] = Field(
        default_factory=list, description="Список гостей (имена/обозначения из письма)"
    )
    room_type: str | None = Field(default=None, description="Тип номера (например, Double, Suite)")
    email_subject: str | None = Field(default=None, description="Тема письма, если известна")


class UserIntentionSchema(BaseModel):
    """Structured capture of the user's wishes for the outgoing hotel email.

    The booking pipeline extracts two kinds of text from what the user forwards to the bot:
    the booking confirmation/voucher itself (handled by :class:`ExtractedBookingSchema`) and
    the short cover note the user may have written on top of it. This schema targets the
    latter — the free-form requests the user wants forwarded to the hotel.

    It is produced by the ``get_user_intention`` node, which is the terminal node of the
    email graph: its output is what gets composed into the final message to the hotel.
    """

    wishes: list[str] = Field(
        default_factory=list,
        description=(
            "Свободно сформулированные пожелания пользователя к отелю "
            "(ранний заезд, тихий номер, детская кроватка и т. п.). "
            "Каждый элемент — отдельная короткая просьба на языке пользователя. "
            "Пустой список, если явных пожеланий нет."
        ),
    )
    no_wishes_detected: bool = Field(
        default=False,
        description=(
            "True, если явных пожеланий пользователя к отелю не обнаружено. "
            "False, если пожелания есть. "
        ),
    )


class UserReplyClassification(BaseModel):
    """Classification of a single user reply during the wishes-collection loop.

    Produced by ``get_user_intention_loop`` for each answer the user sends back after an
    ``interrupt``: either the request is cancelled, the wishes are understood, or the reply is
    unclear (empty wishes, not cancelled) and the loop asks again.
    """

    cancelled: bool = Field(
        default=False,
        description="True, если пользователь явно отказался/отменил задание.",
    )
    wishes: list[str] = Field(
        default_factory=list,
        description="Понятые пожелания. Пусто, если ответ непонятен или отменён.",
    )
