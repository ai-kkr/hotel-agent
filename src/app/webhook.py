from email.utils import parseaddr

import fastapi
from aiogram.utils.text_decorations import html_decoration
from fastapi import APIRouter
from langchain_core.messages import HumanMessage

from src.bot.utils import send_formatted
from src.context import AppContext
from src.db.models import ClientORM
from src.db.repositories import ClientRepository, DuplicateForwardedEmailError
from src.integrations.mailtrap.mailtrap_inbound.models.message_details import MessageDetails
from src.integrations.mailtrap.webhooks import (
    InboundWebhookPayload,
)
from src.logging import get_logger
from src.temporal.client import agent_step

from .dependencies import AppSession, verify_mailtrap_signature

router = APIRouter()

lg = get_logger(__name__)


def extract_email(from_header: str | None | object) -> str | None:
    """Parse an RFC 5322 ``From`` header (``"Name <addr>"``) into a bare lowercase email.

    Returns ``None`` when the value is missing/Unset or doesn't look like an address.
    """
    if not isinstance(from_header, str):
        return None
    _, addr = parseaddr(from_header)
    addr = addr.strip().lower()
    if "@" not in addr or "." not in addr.split("@", 1)[1]:
        return None
    return addr


@router.post("/send_test_email", dependencies=[fastapi.Depends(verify_mailtrap_signature)])
async def send_test_email(
    payload: InboundWebhookPayload,
    sess: AppSession,
    ctx: AppContext,
    background_tasks: fastapi.BackgroundTasks,
) -> None:
    client_repo = ClientRepository(sess)
    for event in payload.events:
        client = await client_repo.get_client_by_inbox_id(event.inbox_id)
        if client is None:
            lg.warning(
                "Received inbound event for unknown inbox",
                inbox_id=event.inbox_id,
                message_id=event.message_id,
            )
            continue
        lg.info("Received inbound event", webhook_event=event.model_dump(by_alias=True))
        try:
            msg = await ctx.mailtrap_client.get_message(
                message_id=event.message_id, inbox_id=event.inbox_id
            )
        except AssertionError as e:
            raise fastapi.HTTPException(
                status_code=502,
                detail=f"Failed to fetch inbound message: {e}",
            ) from e

        assert isinstance(msg, MessageDetails), f"Expected MessageDetails, got {type(msg)}"

        # A hotel reply carries the id of an outbound email we sent in its In-Reply-To header;
        # a forwarded booking does not. Route accordingly.
        outbound = (
            await client_repo.get_outbound_by_message_id(msg.in_reply_to)
            if msg.in_reply_to
            else None
        )
        lg.info(
            "inbound.route",
            client_id=client.id,
            in_reply_to=msg.in_reply_to,
            routed_to="hotel_reply" if outbound is not None else "forwarded",
            matched_outbound_id=outbound.message_id if outbound is not None else None,
        )
        if outbound is not None:
            await _handle_hotel_reply(client, ctx, msg, background_tasks)
            continue

        try:
            await _apply_client_email(client, client_repo, ctx, msg)
        except DuplicateForwardedEmailError:
            lg.warning(
                "Duplicate forwarded email detected",
                client_id=client.id,
                message_id=msg.message_id,
            )
            continue
        email = await client_repo.add_forwarded_email(client.id, msg)
        if client.telegram_id is not None:
            await send_formatted(
                ctx.bot,
                client.telegram_id,
                _format_inbound_notification(
                    title="📨 Новое письмо",
                    sender=msg.from_ or "неизвестный отправителя",
                    subject=msg.subject,
                    footer="Приступаю к обработке…",
                ),
            )
        background_tasks.add_task(
            agent_step,
            update={"messages": [HumanMessage(content=f"forwarded email:\n{email.data.text_body}")]},
            client=client,
        )


async def _handle_hotel_reply(
    client: ClientORM,
    ctx: AppContext,
    msg: MessageDetails,
    background_tasks: fastapi.BackgroundTasks,
) -> None:
    """Feed a hotel reply back into the agent as a ``hotel reply:`` turn.

    The hotel email's Message-ID and subject are passed as a ``state_update`` merge (applied inside
    the workflow before the turn) so ``reply_to_hotel`` can thread the next reply, then the reply
    body drives the agent turn.
    """
    lg.info(
        "Received hotel reply",
        client_id=client.id,
        message_id=msg.message_id,
        in_reply_to=msg.in_reply_to,
    )
    if client.telegram_id is not None:
        await send_formatted(
            ctx.bot,
            client.telegram_id,
            _format_inbound_notification(
                title="🏨 Ответ от отеля",
                sender=msg.from_ or "отель",
                subject=msg.subject,
            ),
        )
    body = msg.text_body or msg.html_body or ""
    background_tasks.add_task(
        agent_step,
        update={"messages": [HumanMessage(content=f"hotel reply:\n{body}")]},
        client=client,
        state_update={
            "last_hotel_message_id": msg.message_id,
            "last_hotel_subject": msg.subject,
        },
    )


def _format_inbound_notification(
    *,
    title: str,
    sender: object,
    subject: object,
    footer: str | None = None,
) -> str:
    """Build an HTML notification about an inbound email for the chat.

    Keeps to the formatting the agent itself uses (bold labels, no headers) so it renders
    consistently via ``send_formatted`` (``parse_mode=HTML``). ``sender``/``subject`` come from the
    Mailtrap ``MessageDetails`` model as ``None | str | Unset``; we normalise both to plain strings
    and HTML-escape them, since they are uncontrolled email content.
    """
    sender_text = sender if isinstance(sender, str) and sender else "неизвестный отправитель"
    subject_text = subject if isinstance(subject, str) and subject else "(без темы)"
    q = html_decoration.quote
    lines = [
        f"<b>{q(title)}</b>",
        f"<b>От:</b> {q(sender_text)}",
        f"<b>Тема:</b> {q(subject_text)}",
    ]
    if footer:
        lines.append("")
        lines.append(footer)
    return "\n".join(lines)


async def _apply_client_email(
    client: ClientORM,
    client_repo: ClientRepository,
    ctx: AppContext,
    msg: MessageDetails,
):
    if client.email is not None:
        return
    parsed_email = extract_email(msg.from_)
    if parsed_email is None:
        return
    owner = await client_repo.get_client_by_email(parsed_email)
    if owner is not None and owner.id != client.id:
        lg.warning(
            "Email already used by another client",
            client_id=client.id,
            email=parsed_email,
            owner_id=owner.id,
        )
        if client.telegram_id is not None:
            await ctx.bot.send_message(
                chat_id=client.telegram_id,
                text=(
                    "Не смог привязать email "
                    f"{html_decoration.quote(parsed_email)} — пользователь с таким адресом"
                    " уже зарегистрирован."
                ),
            )
    else:
        client.email = parsed_email
        lg.info(
            "Stored client email from inbound message",
            client_id=client.id,
            email=parsed_email,
        )
