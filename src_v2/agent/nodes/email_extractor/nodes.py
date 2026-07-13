"""Nodes of the email-extraction graph.

Three stages:

* :func:`email_extractor_node` — parses the forwarded confirmation into
  :class:`~src_v2.agent.nodes.email_extractor.schemas.ExtractedBookingSchema` (with retry on
  parse failure).
* :func:`search_agent_node` — tool-calling agent that looks up the hotel's contact email when
  the confirmation does not contain one.
* :func:`get_user_intention` — terminal node that extracts the user's wishes from the cover
  note on top of the forwarded message.
"""

from typing import cast

from langchain.messages import HumanMessage
from langchain_core.messages import AIMessage
from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt

from infrastructure.config import get_settings
from infrastructure.logging import get_logger
from src_v2.agent.prompts import (
    SYSTEM_CLASSIFY_USER_REPLY,
    SYSTEM_EXTRACT_EMAIL,
    SYSTEM_LETTER_TO_HOTEL,
    SYSTEM_SEARCH_EMAIL,
    SYSTEM_USER_INTENTION,
)
from src_v2.agent.types import AgentContext, MessageText, StructuredOutputWithRaw

from .schemas import ExtractedBookingSchema, UserIntentionSchema, UserReplyClassification
from .state import (
    EmailInputState,
    EmailOutputState,
    EmailState,
    EmailToHotelInputState,
    EmailToHotelOutputState,
    SendEmailToHotelInputState,
    SendEmailToHotelOutputState,
)
from .tools import tools

__all__ = [
    "email_extractor_node",
    "get_user_intention",
    "get_user_intention_loop",
    "search_agent_node",
]

log = get_logger(__name__)

#: How many times the wishes-collection loop re-asks before giving up and ending the graph.
MAX_INTENTION_ATTEMPTS = 3

#: Question surfaced to the user (via ``stream_writer`` and the ``interrupt`` value) when their
#: wishes could not be derived from the forwarded cover note.
ASK_WISHES_TEXT = (
    "Не удалось понять пожелания из письма. Опишите одним сообщением, что передать отелю "
    "(или пришлите «отмена», чтобы отказаться)."
)


async def email_extractor_node(
    state: EmailInputState,
    runtime: Runtime[AgentContext],
) -> EmailOutputState:
    email_body = state["email_body"]
    writer = runtime.stream_writer
    model = runtime.context.model.with_structured_output(
        ExtractedBookingSchema,
        include_raw=True,
        method="function_calling",
    )
    metadata = {
        "subject": state.get("subject"),
        "reply_to": state.get("reply_to"),
        "in_reply_to": state.get("in_reply_to"),
    }
    messages = state.get("messages") or [
        HumanMessage(content=f"metadata: {metadata}\n\n{email_body}"),
    ]
    if error := state.get("error"):
        messages.append(HumanMessage(content=f"Previous parsing error: {error}"))
    if not error:
        writer(MessageText(text="Читаю письмо и извлекаю данные о бронировании..."))
    attempt = state.get("attempts", 0) + 1
    log.info(
        "email_extractor.start",
        attempt=attempt,
        had_previous_error=bool(error),
        body_len=len(email_body) if email_body else 0,
    )
    data: StructuredOutputWithRaw[ExtractedBookingSchema] = await model.ainvoke(
        [
            SYSTEM_EXTRACT_EMAIL,
            *messages,
        ]
    )  # ty:ignore[invalid-assignment]
    if data["parsing_error"] is not None:
        log.warning(
            "email_extractor.parse_failed",
            attempt=attempt,
            error=str(data["parsing_error"]),
        )
        return {
            "parsed_email": None,
            "hotel_email": None,
            "messages": [*messages, cast(AIMessage, data["raw"])],
            "error": str(data["parsing_error"]),
            "attempts": attempt,
        }
    parsed: ExtractedBookingSchema = data["parsed"]
    log.info(
        "email_extractor.extracted",
        attempt=attempt,
        hotel_name=parsed.hotel_name if parsed else None,
        hotel_email=str(parsed.hotel_email) if parsed and parsed.hotel_email else None,
        booking_ref=parsed.booking_ref if parsed else None,
    )
    writer(MessageText(text="Данные о бронировании извлечены."))
    return {
        "parsed_email": parsed,
        "hotel_email": parsed.hotel_email if parsed is not None else None,
        "error": None,
        "attempts": attempt,
        "messages": [
            *messages,
            cast(AIMessage, data["raw"]),
        ],
    }


async def search_agent_node(
    state: EmailOutputState, runtime: Runtime[AgentContext]
) -> EmailOutputState:
    model = runtime.context.model.bind_tools(tools)
    writer = runtime.stream_writer
    messages = [
        SYSTEM_SEARCH_EMAIL,
        *state["messages"],
    ]
    log.info(
        "search_agent.start",
        search_rounds=state.get("search_rounds", 0),
        messages=len(messages),
    )
    if state.get("search_rounds", 0) == 0:
        writer(MessageText(text="Ищу контактный email отеля в интернете..."))
    response = await model.ainvoke(messages)
    log.info(
        "search_agent.done",
        has_tool_calls=bool(getattr(response, "tool_calls", None)),
    )
    return {
        "messages": [response],
    }


async def get_user_intention(
    state: EmailToHotelInputState,
    runtime: Runtime[AgentContext],
) -> EmailToHotelOutputState:
    """Terminal node: extract the user's wishes from the forwarded message.

    Reads only the cover note the user wrote on top of the booking confirmation and packs
    the detected requests into :class:`UserIntentionSchema`. On a parsing failure the node
    degrades gracefully — it returns an empty wish list rather than crashing the graph,
    so the already-known ``hotel_email`` still reaches the output.
    """
    writer = runtime.stream_writer
    writer(MessageText(text="Собираю пожелания пользователя к отелю..."))
    model = runtime.context.model.with_structured_output(
        UserIntentionSchema, include_raw=True, method="function_calling"
    )
    data: StructuredOutputWithRaw[UserIntentionSchema] = await model.ainvoke(
        [
            SYSTEM_USER_INTENTION,
            HumanMessage(content=state["email_body"]),
        ]
    )  # ty:ignore[invalid-assignment]
    if data["parsing_error"] is not None:
        log.warning(
            "get_user_intention.parse_failed",
            error=str(data["parsing_error"]),
        )
        return {
            "wishes": [],
            "hotel_email": state["hotel_email"],
        }
    parsed: UserIntentionSchema | None = data["parsed"]
    wishes = parsed.wishes if parsed is not None else []
    log.info("get_user_intention.parsed", wishes=wishes)
    return {
        "wishes": wishes,
        "hotel_email": state["hotel_email"],
    }


async def _classify_user_reply(
    runtime: Runtime[AgentContext], text: str
) -> UserReplyClassification:
    """Classify one user reply from the wishes loop into cancel / wishes / unclear."""
    model = runtime.context.model.with_structured_output(
        UserReplyClassification, include_raw=True, method="function_calling"
    )
    data: StructuredOutputWithRaw[UserReplyClassification] = await model.ainvoke(
        [
            SYSTEM_CLASSIFY_USER_REPLY,
            HumanMessage(content=text),
        ]
    )  # ty:ignore[invalid-assignment]
    if data["parsing_error"] is not None:
        log.warning("get_user_intention_loop.parse_failed", error=str(data["parsing_error"]))
        # A parse failure means we could not understand the reply — treat as unclear and re-ask.
        return UserReplyClassification()
    return data["parsed"] or UserReplyClassification()


async def get_user_intention_loop(
    state: EmailState, runtime: Runtime[AgentContext]
) -> Command:
    """Collect the user's wishes interactively when none were found in the cover note.

    Loops over ``interrupt``: each iteration surfaces a question to the client, pauses until a
    reply is supplied via ``Command(resume=...)``, then classifies it. On classified wishes it
    hands off to ``send_letter_to_hotel``; on cancellation (explicit or an empty/non-text resume)
    or after :data:`MAX_INTENTION_ATTEMPTS` unclear replies it goes straight to ``END``.

    The ``interrupt`` calls are indexed by invocation order, so the local ``attempts`` counter
    stays consistent across resume replays — no state field is needed to track progress.
    """
    writer = runtime.stream_writer
    attempts = 0
    while attempts < MAX_INTENTION_ATTEMPTS:
        attempts += 1
        prompt = ASK_WISHES_TEXT if attempts == 1 else f"Не понял ответ. {ASK_WISHES_TEXT}"
        writer(MessageText(text=prompt))
        answer = interrupt({"prompt": prompt, "attempt": attempts})

        # No textual answer from the client → treat as an abort.
        if not isinstance(answer, str) or not answer.strip():
            log.info("get_user_intention_loop.cancelled", reason="empty_reply", attempt=attempts)
            return Command(
                update={"cancelled": True, "intention_attempts": attempts},
                goto=END,
            )

        classification = await _classify_user_reply(runtime, answer)
        log.info(
            "get_user_intention_loop.classify",
            attempt=attempts,
            cancelled=classification.cancelled,
            wishes=classification.wishes,
        )
        if classification.cancelled:
            return Command(
                update={"cancelled": True, "intention_attempts": attempts},
                goto=END,
            )
        if classification.wishes:
            return Command(
                update={
                    "wishes": classification.wishes,
                    "cancelled": False,
                    "intention_attempts": attempts,
                },
                goto="send_letter_to_hotel",
            )
        # Unclear reply — loop and ask again on the next interrupt slot.

    writer(MessageText(text="Не удалось собрать пожелания — завершаю без отправки письма."))
    log.info("get_user_intention_loop.exhausted", attempts=attempts)
    return Command(
        update={"cancelled": True, "intention_attempts": attempts},
        goto=END,
    )


def _format_booking_info(parsed: ExtractedBookingSchema) -> str:
    """Render the extracted booking as a compact, model-friendly context block."""
    guests = ", ".join(parsed.guests) if parsed.guests else "—"
    lines = [
        f"Отель: {parsed.hotel_name}",
        f"Код брони: {parsed.booking_ref or '—'}",
        f"Заезд: {parsed.check_in or '—'}",
        f"Выезд: {parsed.check_out or '—'}",
        f"Тип номера: {parsed.room_type or '—'}",
        f"Гости: {guests}",
    ]
    return "\n".join(lines)


async def send_user_intention_to_hotel(
    state: SendEmailToHotelInputState,
    runtime: Runtime[AgentContext],
) -> SendEmailToHotelOutputState:
    """Terminal node: compose the letter to the hotel from the extracted booking + wishes.

    Generates the outgoing email body via the model (guided by ``SYSTEM_LETTER_TO_HOTEL``)
    and stores it in the ``letter`` channel. Actual delivery through
    :class:`OutboundMailGateway` is intentionally not wired here yet — it requires
    ``booking_id`` / ``sender`` / ``reply_to`` / ``subject`` / ``idempotency_key`` which are
    not currently available in the graph state or :class:`AgentContext`.
    """
    writer = runtime.stream_writer
    writer(MessageText(text="Составляю письмо в отель..."))
    hotel_email = state["hotel_email"]
    wishes = state["wishes"]
    parsed = state["parsed_email"]
    hotel_language = parsed.hotel_language if parsed is not None else "en"
    log.info(
        "send_user_intention_to_hotel.compose",
        hotel_email=str(hotel_email),
        wishes=wishes,
        hotel_name=parsed.hotel_name if parsed else None,
        hotel_language=hotel_language,
    )
    model = runtime.context.model
    booking_info = _format_booking_info(parsed) if parsed is not None else "—"
    wishes_block = "\n".join(f"- {w}" for w in wishes) if wishes else "—"
    letter = await model.ainvoke(
        [
            SYSTEM_LETTER_TO_HOTEL,
            HumanMessage(
                content=(
                    f"hotel_language: {hotel_language}\n\n"
                    "Данные бронирования:\n"
                    f"{booking_info}\n\n"
                    "Пожелания гостя:\n"
                    f"{wishes_block}"
                )
            ),
        ]
    )
    letter_text = letter.content if isinstance(letter.content, str) else str(letter.content)
    gateway = runtime.context.outbound_mail_gateway
    settings = get_settings()
    to_email = str(hotel_email) if not settings.is_dev else state.get("from_")
    if to_email is not None:
        await gateway.send(
            sender=runtime.context.from_email,
            to=[to_email],
            subject=_build_subject(state),
            text=letter_text,
        )
    writer(MessageText(text=f"Письмо в отель составлено и готово к отправке.\n{letter_text}"))
    return {
        "letter": letter_text,
    }


def _build_subject(state: SendEmailToHotelInputState) -> str:
    """Build the email subject line for the outgoing letter to the hotel.

    Uses the original subject from the forwarded message if available, otherwise falls back
    to a generic "Booking Inquiry" subject.
    """
    original_subject = state.get("subject")
    parsed = state.get("parsed_email")
    if original_subject:
        return f"Fwd: {original_subject}"
    if parsed and parsed.email_subject:
        return f"Fwd: {parsed.email_subject}"
    if parsed and parsed.booking_ref:
        return f"Booking Inquiry: {parsed.booking_ref}"
    return "Booking Inquiry"
