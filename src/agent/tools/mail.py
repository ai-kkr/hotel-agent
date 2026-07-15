"""Mail-domain tools: ``send_wishes_to_hotel`` and ``reply_to_hotel``.

These compose the outgoing letter / reply, send it via Mailtrap, and persist the outbound message
id so the inbound webhook can later match a hotel reply by its ``In-Reply-To`` header.
"""

import uuid

from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.types import Command

from src.config import get_settings
from src.logging import get_logger

from ..context import EmailContext
from ..exceptions import SelfCorrectionError
from ..prompts import SYSTEM_LETTER_TO_HOTEL
from ..state import EmailState
from ..types import MessageText
from .booking import missing_booking_fields
from .utils import ack

__all__ = ["reply_to_hotel", "send_wishes_to_hotel"]

log = get_logger(__name__)


def _format_booking(state: EmailState) -> str:
    """Render the booking fields as a compact, model-friendly context block for the letter."""
    guests = ", ".join(state.get("guests") or []) or "—"
    ref = state.get("booking_ref")
    lines = [
        f"Отель: {state.get('hotel_name') or '—'}",
        f"Код брони: {ref or '—'}",
        f"Заезд: {state.get('from_date') or '—'}",
        f"Выезд: {state.get('to_date') or '—'}",
        f"Гости: {guests}",
    ]
    return "\n".join(lines)


async def _compose_letter(state: EmailState, wishes: list[str]) -> str:
    """Generate the hotel letter body via the LLM, in ``hotel_language``."""
    # Lazy import avoids the context↔tools import cycle.
    from src.context import get_context

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
        ],
        config={
            "tags": [
                # Suppress this internal LLM call from the graph's ``messages`` stream: otherwise
                # its AIMessage (the composed letter body) inherits the graph callback config via
                # contextvars and leaks into ``stream_graph``, which forwards it to Telegram.
                # ``nostream`` is langgraph's TAG_NOSTREAM — on_chat_model_start skips runs tagged
                # with it (langgraph/pregel/_messages.py). The result still comes back from
                # ``ainvoke`` as usual; only streaming/observability is suppressed.
                "nostream",
            ]
        },
    )
    return response.content if isinstance(response.content, str) else str(response.content)


def _resolve_recipient(runtime: ToolRuntime[EmailContext, EmailState]) -> str:
    """Outbound recipient: the user's own email in dev mode, the hotel in production."""
    if get_settings().is_dev:
        return runtime.context.get("user_email") or ""
    return runtime.state.get("hotel_email") or ""


def _make_message_id(from_email: str | None) -> str:
    """Generate a unique RFC 5322 ``Message-ID`` (``<token@domain>``) that we control.

    Mailtrap's send-response ``message_ids`` are internal UUIDs, NOT the RFC ``Message-ID`` header
    the recipient sees — and a reply's ``In-Reply-To`` echoes that header. So we set our own
    ``Message-ID`` and persist it; the inbound webhook then matches a reply by it.
    """
    domain = (from_email or "").split("@", 1)[-1] or "mailtrap.local"
    return f"<{uuid.uuid4().hex}@{domain}>"


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
    # Lazy imports: src.context and the DB layer pull in this package's neighbours, so importing
    # them at module top would create a cycle.
    from src.context import get_context
    from src.db.repositories import ClientRepository
    from src.db.session import session_context

    ctx = get_context()
    # Stamp our own Message-ID so a later hotel reply can be matched by ``In-Reply-To``. Merged on
    # top of any caller headers (``In-Reply-To``/``References`` for ``reply_to_hotel``); we never
    # clobber those.
    from_email = runtime.context.get("from_email") or ""
    message_id = _make_message_id(from_email)
    sent_headers = {**(headers or {}), "Message-ID": message_id}
    response = await ctx.mailtrap_client.send(
        sender=from_email,
        to=[to],
        subject=subject,
        text=text,
        headers=sent_headers,
        reply_to=runtime.context.get("reply_to"),
    )
    log.info(
        "mail.sent",
        message_id=message_id,
        mailtrap_ids=response.message_ids,
        to=to,
    )
    client_id = runtime.context.get("client_id")
    if client_id is not None:
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

    After calling this tool, STOP. The tool already tells the guest the progress. NEVER write the
    letter body in chat and do not re-summarise it — the guest does not see the letter.

    Args:
        wishes: The user's wishes to send to the hotel.
    """
    state = runtime.state
    missing = missing_booking_fields(state)
    if missing:
        raise SelfCorrectionError(
            "Не хватает данных брони: " + ", ".join(missing) + ". "
            "Уточни у пользователя или заполни set_booking_info перед отправкой."
        )
    log.info("tool.send_wishes_to_hotel", wishes=wishes)
    letter = await _compose_letter(state, wishes)
    ref = state.get("booking_ref")
    ref_part = f" [{ref}]" if ref else ""
    subject = (
        f"Booking inquiry — {state.get('hotel_name') or ''}{ref_part} "
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
            "messages": [
                ack(
                    runtime,
                    content=(
                        "Письмо отправлено, статус уже показан госту. На этом ход завершён: "
                        "БОЛЬШЕ НИЧЕГО НЕ ПИШИ — не выводи и не пересказывай текст письма, "
                        "гостю он не нужен."
                    ),
                )
            ],
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

    After calling this tool, STOP. NEVER echo the reply body back into the chat and do not
    re-summarise it — the guest does not see the reply text.

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
            "messages": [
                ack(
                    runtime,
                    content=(
                        "Ответ отелю отправлен. На этом ход завершён: БОЛЬШЕ НИЧЕГО НЕ ПИШИ — "
                        "не выводи и не пересказывай текст ответа, гостю он не нужен."
                    ),
                )
            ],
        }
    )
