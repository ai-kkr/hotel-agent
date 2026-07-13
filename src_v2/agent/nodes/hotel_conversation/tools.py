"""Tools available to the hotel-conversation agent.

These are the agent's actions: record booking details, forward the user's wishes to the hotel,
narrate progress, and cancel when stuck. Tools that mutate the graph state
(``set_booking_info``, ``send_wishes_to_hotel``, ``cancel_task``, ``inform_step``) return a
:class:`langgraph.types.Command(update=...)`; a bare ``dict`` return would be treated as the
``ToolMessage`` content by ``ToolNode`` and would *not* update state.

State-changing tools here intentionally keep the agent's runtime :class:`EmailContext` serializable:
non-serializable dependencies (the outbound mail gateway) are fetched via
:func:`src_v2.context.get_context` inside the tool, never stored on the context.
"""

from typing import Literal, cast

from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

from infrastructure.config import get_settings
from infrastructure.logging import get_logger
from src_v2.agent.exceptions import SelfCorrectionError
from src_v2.agent.prompts import SYSTEM_LETTER_TO_HOTEL
from src_v2.agent.types import MessageText

from .context import EmailContext
from .state import EmailState

__all__ = [
    "cancel_task",
    "inform_step",
    "reply_to_hotel",
    "send_wishes_to_hotel",
    "set_booking_info",
    "tools",
]

log = get_logger(__name__)


def _ack(runtime: ToolRuntime[EmailContext, EmailState], content: str = "Success") -> ToolMessage:
    """Build the acknowledgement ToolMessage that closes a tool call in the agent's history."""
    return ToolMessage(content=content, tool_call_id=runtime.tool_call_id)


# Booking fields that ``send_wishes_to_hotel`` requires to be non-empty before it can send.
_REQUIRED_BOOKING_FIELDS: tuple[str, ...] = (
    "hotel_name",
    "from_date",
    "to_date",
    "hotel_email",
    "guests",
    "hotel_language",
)


def _missing_booking_fields(state: EmailState) -> list[str]:
    """Names of required booking fields that are absent/empty in ``state``."""
    missing: list[str] = []
    for field in _REQUIRED_BOOKING_FIELDS:
        value = state.get(field)
        if value is None or value == [] or value == "":
            missing.append(field)
    return missing


# Russian labels for the booking fields, in display order.
_BOOKING_LABELS: tuple[tuple[str, str], ...] = (
    ("hotel_name", "Отель"),
    ("from_date", "Заезд"),
    ("to_date", "Выезд"),
    ("hotel_email", "Email отеля"),
    ("guests", "Гости"),
    ("hotel_language", "Язык письма"),
)

#: Map ``hotel_language`` code → human label for the booking summary.
_LANGUAGE_LABELS: dict[str, str] = {"ru": "Русский", "zh": "Китайский", "en": "Английский"}


def _format_booking_summary(
    *,
    hotel_name: str | None,
    from_date: str | None,
    to_date: str | None,
    hotel_email: str | None,
    guests: list[str] | None,
    hotel_language: str | None,
) -> MessageText | None:
    """Build a Russian markdown-list summary of the non-empty booking fields being set.

    Returns ``None`` when every field is empty (nothing to announce).
    """
    values: dict[str, object] = {
        "hotel_name": hotel_name,
        "from_date": from_date,
        "to_date": to_date,
        "hotel_email": hotel_email,
        "guests": guests,
        "hotel_language": _LANGUAGE_LABELS.get(hotel_language, hotel_language) if hotel_language else None,
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
    from_date: str | None = None,
    to_date: str | None = None,
    hotel_email: str | None = None,
    guests: list[str] | None = None,
    hotel_language: Literal["ru", "zh", "en"] | None = None,
):
    """Record booking details as you learn them. Leave a field null (omit it) to keep it unchanged.

    Call this incrementally as you parse the forwarded confirmation or clarify details with the
    user. A null argument is a no-op (the existing value is kept via the ``booking_field``
    reducer). All listed fields must be filled before ``send_wishes_to_hotel``.

    Args:
        hotel_name: Hotel name.
        from_date: Check-in date (``YYYY-MM-DD``).
        to_date: Check-out date (``YYYY-MM-DD``).
        hotel_email: Hotel contact email.
        guests: Guest names/labels.
        hotel_language: Language for the letter to the hotel — ``ru`` (Russia), ``zh`` (China),
            ``en`` (any other country). Determine from the hotel's country.
    """
    log.info(
        "tool.set_booking_info",
        hotel_name=hotel_name,
        from_date=from_date,
        to_date=to_date,
        hotel_email=hotel_email,
        guests=guests,
        hotel_language=hotel_language,
    )
    summary = _format_booking_summary(
        hotel_name=hotel_name,
        from_date=from_date,
        to_date=to_date,
        hotel_email=hotel_email,
        guests=guests,
        hotel_language=hotel_language,
    )
    if summary is not None:
        runtime.stream_writer(summary)
    return Command(
        update={
            "hotel_name": hotel_name,
            "from_date": from_date,
            "to_date": to_date,
            "hotel_email": hotel_email,
            "guests": guests,
            "hotel_language": hotel_language,
            "messages": [_ack(runtime)],
        }
    )


@tool
async def inform_step(step: str, runtime: ToolRuntime[EmailContext, EmailState]):
    """Narrate a progress step to the user (no state side-effect besides the ack).

    Use this to keep the user informed about what you are doing, e.g. "Looking up the hotel
    contact email…". Do not abuse it — one short message per meaningful step.

    Args:
        step: A short description of the current step.
    """
    log.info("tool.inform_step", step=step)
    runtime.stream_writer(MessageText(text=step))
    return Command(update={"messages": [_ack(runtime)]})


def _format_booking(state: EmailState) -> str:
    """Render the booking fields as a compact, model-friendly context block."""
    guests = ", ".join(state.get("guests") or []) or "—"
    return "\n".join(
        [
            f"Отель: {state.get('hotel_name') or '—'}",
            f"Заезд: {state.get('from_date') or '—'}",
            f"Выезд: {state.get('to_date') or '—'}",
            f"Гости: {guests}",
        ]
    )


async def _compose_letter(state: EmailState, wishes: list[str]) -> str:
    """Generate the hotel letter body via the LLM, in ``hotel_language``."""
    # Lazy import avoids the context↔tools import cycle.
    from src_v2.context import get_context

    model = get_context().model
    wishes_block = "\n".join(f"- {w}" for w in wishes) if wishes else "—"
    response = await model.ainvoke(
        [
            SYSTEM_LETTER_TO_HOTEL,
            HumanMessage(
                content=(
                    f"hotel_language: {state.get('hotel_language') or 'en'}\n\n"
                    "Данные бронирования:\n"
                    f"{_format_booking(state)}\n\n"
                    "Пожелания гостя:\n"
                    f"{wishes_block}"
                )
            ),
        ]
    )
    return response.content if isinstance(response.content, str) else str(response.content)


def _resolve_recipient(runtime: ToolRuntime[EmailContext, EmailState]) -> str:
    """Outbound recipient: the user's own email in dev mode, the hotel in production."""
    if get_settings().is_dev:
        return runtime.context.get("user_email") or ""
    return runtime.state.get("hotel_email") or ""


async def _send_and_persist(
    runtime: ToolRuntime[EmailContext, EmailState],
    *,
    to: str,
    subject: str,
    text: str,
    headers: dict[str, str] | None,
    in_reply_to: str | None,
) -> str:
    """Send the email via Mailtrap and persist an ``outbound_emails`` record; return message id."""
    # Lazy imports: src_v2.context and the DB layer both pull in this module's neighbours, so
    # importing them at module top would create a cycle.
    from src_v2.context import get_context
    from src_v2.db.repositories import ClientRepository
    from src_v2.db.session import session_context

    ctx = get_context()
    response = await ctx.mailtrap_client.send(
        sender=runtime.context.get("from_email") or "",
        to=[to],
        subject=subject,
        text=text,
        headers=headers,
        reply_to=runtime.context.get("reply_to"),
    )
    message_id = (response.message_ids or [""])[0]
    client_id = runtime.context.get("client_id")
    if message_id and client_id is not None:
        async with session_context(ctx.session_factory) as session:
            repo = ClientRepository(session)
            await repo.add_outbound(
                message_id=message_id,
                client_id=client_id,
                subject=subject,
                in_reply_to=in_reply_to,
            )
    return message_id


@tool
async def send_wishes_to_hotel(
    wishes: list[str],
    runtime: ToolRuntime[EmailContext, EmailState],
):
    """Compose a letter from the user's wishes and send it to the hotel.

    Requires the full booking info (``set_booking_info``), including ``hotel_language``. The
    letter is generated in that language; in dev mode it is sent to the user's own email instead
    of the hotel. The sent message id is stored so the inbound webhook can later match a hotel
    reply by its ``In-Reply-To`` header.

    Args:
        wishes: The user's wishes to send to the hotel.
    """
    state = runtime.state
    missing = _missing_booking_fields(state)
    if missing:
        raise SelfCorrectionError(
            "Не хватает данных брони: " + ", ".join(missing) + ". "
            "Уточни у пользователя или заполни set_booking_info перед отправкой."
        )
    log.info("tool.send_wishes_to_hotel", wishes=wishes)
    letter = await _compose_letter(state, wishes)
    subject = (
        f"Booking inquiry — {state.get('hotel_name') or ''} "
        f"({state.get('from_date') or '?'}…{state.get('to_date') or '?'})"
    )
    runtime.stream_writer(MessageText(text="Отправляю письмо в отель…"))
    message_id = await _send_and_persist(
        runtime,
        to=_resolve_recipient(runtime),
        subject=subject,
        text=letter,
        headers=None,
        in_reply_to=None,
    )
    runtime.stream_writer(MessageText(text="Письмо отелю отправлено. Жду ответ."))
    return Command(
        update={
            "user_wishes": wishes,
            "last_outbound_message_id": message_id,
            "messages": [_ack(runtime)],
        }
    )


@tool
async def reply_to_hotel(
    message: str,
    runtime: ToolRuntime[EmailContext, EmailState],
):
    """Reply to the hotel's last email in the same thread.

    ``message`` is the full reply body, written by you in the hotel's language, plain text, no
    markdown. The tool sets ``In-Reply-To``/``References`` and a ``Re:`` subject so it threads
    under the hotel's email. Only call this after a hotel reply has arrived.

    Args:
        message: The reply body to send to the hotel.
    """
    state = runtime.state
    hotel_message_id = state.get("last_hotel_message_id")
    if not hotel_message_id:
        raise SelfCorrectionError(
            "Нет письма отеля для ответа. reply_to_hotel вызывается только после того, как "
            "пришёл ответ отеля."
        )
    log.info("tool.reply_to_hotel", in_reply_to=hotel_message_id)
    subject = "Re: " + (state.get("last_hotel_subject") or "")
    headers = {"In-Reply-To": hotel_message_id, "References": hotel_message_id}
    runtime.stream_writer(MessageText(text="Отправляю ответ отелю…"))
    message_id = await _send_and_persist(
        runtime,
        to=_resolve_recipient(runtime),
        subject=subject,
        text=message,
        headers=headers,
        in_reply_to=hotel_message_id,
    )
    return Command(
        update={
            "last_outbound_message_id": message_id,
            "messages": [_ack(runtime)],
        }
    )


@tool
async def cancel_task(
    reason: str,
    runtime: ToolRuntime[EmailContext, EmailState],
):
    """Cancel the task — something blocking made it impossible to proceed.

    Use when the hotel email cannot be found or the user declined to continue. The reason is
    surfaced to the user.

    Args:
        reason: A short explanation of why the task is being cancelled.
    """
    log.info("tool.cancel_task", reason=reason)
    runtime.stream_writer(MessageText(text="Задача отменена: " + reason))
    return Command(
        update={
            "task_cancelled": True,
            "messages": [_ack(runtime, content="Task cancelled")],
        }
    )


tools = [
    set_booking_info,
    send_wishes_to_hotel,
    reply_to_hotel,
    inform_step,
    cancel_task,
]
