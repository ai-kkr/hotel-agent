"""Surface-agnostic conversational agent (design D1, D4, D9; spec: telegram-surface).

A LangGraph ``create_agent`` ReAct agent that holds a live, multi-turn dialogue with a client over
an arbitrary surface. It is **surface-agnostic**: it imports no channel types (no Telegram) and
emits only artifacts (``RequestUserDecision`` / ``CancelBooking``) plus text. A channel adapter
renders the artifacts.

The agent owns dialogue + UX orchestration only. Mutating tools (``delete_task``, ``ask_user``)
emit intents/artifacts that a service executes — the agent performs no side-effects (no workflow
start/cancel, no email/chat send). Read tools (``list_tasks``, ``get_user_mailbox``) go through the
domain ports. Intake is delegated to the core: a forwarded confirmation handed to the agent is
routed through :class:`ChatIntakeService` (not re-implemented).

Per-chat context lives on the checkpointer (``thread_id = chat_id``): ``InMemorySaver`` locally,
``PostgresSaver`` for prod parity (see :mod:`infrastructure.db.langgraph`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.checkpoint.base import BaseCheckpointSaver

from domain.application import ChatIntakeService, MailboxService
from domain.entities import Booking
from domain.enums import BookingLifecycle, Channel
from domain.events import ChatForward
from domain.ids import ClientToken
from domain.intents import CancelBooking, RequestUserDecision, SurfaceArtifact
from domain.ports import BookingRepository, ChannelSessionRepository
from infrastructure.agents.tools import WebFetcher, WebSearcher, build_tools
from infrastructure.db.langgraph import thread_config

SYSTEM_PROMPT = """You are the concierge's live chat assistant. You help a guest communicate with \
their hotel — nothing else.

What you can do:
- Answer general questions about the hotel (menu, services, prices) using web_search / fetch_url.
- Collect a booking: if the guest forwards/pastes a booking confirmation, acknowledge it and rely on \
the system to extract and start negotiating with the hotel. Capture any wishes they mention.
- Summarize the guest's active requests via list_tasks.
- Cancel a request via delete_task (you never cancel silently — confirm what will happen).
- Ask a multiple-choice question via ask_user when you need the guest to pick an option.

Process you follow for a new booking: collect the booking → confirm intent (ask_user with options \
like early check-in, higher floor, late check-out) → the system negotiates with the hotel → report \
back. Keep replies short and friendly.

After the first message has been sent to the hotel, proactively offer to look up open-source \
information about that hotel (restaurant menu, extra services and prices) using web_search/fetch_url.

Never claim to take an action the system performs (sending email, cancelling a workflow) — say you \
will ask the system to do it. Costs are informational only; never commit the guest to payments."""


@dataclass
class SurfaceDeps:
    """Collaborators the surface agent's tools reach through (all domain ports/services)."""

    mailbox: MailboxService
    sessions: ChannelSessionRepository
    bookings: BookingRepository
    intake: ChatIntakeService
    channel: Channel = Channel.TELEGRAM


@dataclass(frozen=True)
class SurfaceComponents:
    """The LLM building blocks a :class:`SurfaceAgent` shares with the other agents.

    Passed into the runtime wiring (``build_local_app``) so the surface agent can be constructed
    alongside its domain deps. ``None`` disables the surface.
    """

    model: BaseChatModel
    searcher: WebSearcher
    fetcher: WebFetcher
    checkpointer: BaseCheckpointSaver


@dataclass
class SurfaceReply:
    """One conversational turn's output: a chat message + zero or more surface artifacts."""

    text: str
    artifacts: list[SurfaceArtifact] = field(default_factory=list)
    client_token: ClientToken | None = None


@dataclass
class _TurnContext:
    """Per-turn mutable state the tools close over (chat_id + collected artifacts).

    The agent graph is built once; this context is swapped at the start of each ``converse`` call so
    tools always read the current chat and append to the current turn's artifacts.
    """

    chat_id: str | None = None
    artifacts: list[SurfaceArtifact] = field(default_factory=list)


class SurfaceAgent:
    """The surface-agnostic conversational agent.

    Construct once (model + checkpointer + deps); call :meth:`converse` per inbound chat message.
    """

    def __init__(
        self,
        model: BaseChatModel,
        searcher: WebSearcher,
        fetcher: WebFetcher,
        checkpointer: BaseCheckpointSaver,
        deps: SurfaceDeps,
    ) -> None:
        self._deps = deps
        self._ctx = _TurnContext()
        self._agent = create_agent(
            model=model,
            tools=self._build_tools(searcher, fetcher),
            system_prompt=SYSTEM_PROMPT,
            checkpointer=checkpointer,
        )

    async def converse(self, chat_id: str, user_text: str) -> SurfaceReply:
        """Run one turn for the chat identified by ``chat_id``.

        ``chat_id`` is the channel address (e.g. a Telegram chat id); it pins the per-chat
        checkpoint thread. Tools resolve the owning client dynamically via the ChannelSession.
        """
        # Mutate the shared context in place: tools hold a reference to ``self._ctx`` from
        # construction, so rebinding it would leave them reading a stale turn.
        self._ctx.chat_id = chat_id
        self._ctx.artifacts = []
        result = await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": user_text}]},
            config={**thread_config(chat_id), "recursion_limit": 12},
        )
        token = await self._deps.sessions.client_for(self._deps.channel, chat_id)
        return SurfaceReply(text=_last_text(result), artifacts=list(self._ctx.artifacts), client_token=token)

    async def intake_forward(self, chat_id: str, payload: str, cover_text: str, received_at: Any) -> SurfaceReply:
        """Delegate a forwarded confirmation to the core intake (design D2/D6).

        The agent does not extract; it hands the payload to :class:`ChatIntakeService`, which routes
        through the shared extractor + ``start_booking``. Returns a chat reply describing the
        outcome (started, or prompting the guest to initialize their mailbox).
        """
        outcome = await self._deps.intake.handle(
            ChatForward(
                client_token="",  # resolved from the session inside the service
                chat_id=chat_id,
                cover_text=cover_text,
                forwarded_payload=payload,
                received_at=received_at,
                channel=self._deps.channel,
            )
        )
        if outcome.started:
            text = (
                "Got it — I've sent that booking to the concierge. I'll confirm what I'm asking the "
                "hotel once it's underway."
            )
        else:
            text = (
                "I couldn't link that to your account yet. Let me set up your mailbox first "
                "(just say 'set up my mailbox')."
            )
        return SurfaceReply(text=text, artifacts=[], client_token=outcome.client_token)

    # -- tools ---------------------------------------------------------------------

    def _build_tools(self, searcher: WebSearcher, fetcher: WebFetcher) -> list[BaseTool]:
        deps = self._deps
        ctx = self._ctx

        async def get_user_mailbox() -> str:
            """Ensure the guest's private mailbox is set up (lazy, idempotent).

            Creates the mailbox on first call. The address is never returned to you — it is private
            and used internally as the guest's identity anchor.
            """
            await deps.mailbox.resolve_or_create(deps.channel, _require_chat(ctx))
            return "The guest's mailbox is ready."

        async def list_tasks() -> str:
            """List the guest's active bookings and their current status."""
            token = await deps.sessions.client_for(deps.channel, _require_chat(ctx))
            if token is None:
                return "The guest has no mailbox yet — ask them to set one up first."
            bookings = await deps.bookings.bookings_for_client(token)
            active = [b for b in bookings if b.is_active]
            if not active:
                return "The guest has no active requests."
            return "\n".join(f"- {_summarize_booking(b)}" for b in active)

        async def delete_task(booking_id: str) -> str:
            """Ask the system to cancel one of the guest's bookings.

            Args:
                booking_id: The booking id (from list_tasks) to cancel.
            """
            ctx.artifacts.append(CancelBooking(booking_id=booking_id))
            return f"Noted — I'll ask the system to cancel booking {booking_id}."

        async def ask_user(question: str, options: list[str]) -> str:
            """Ask the guest a multiple-choice question.

            Args:
                question: The question to ask.
                options: The distinct choices the guest can pick (2-6 recommended).
            """
            ctx.artifacts.append(RequestUserDecision(question=question, options=list(options)))
            return f"Asked the guest: {question}"

        tools = build_tools(searcher, fetcher)  # web_search + fetch_url (read-only, reused)
        tools += [
            StructuredTool.from_function(coroutine=get_user_mailbox, name="get_user_mailbox"),
            StructuredTool.from_function(coroutine=list_tasks, name="list_tasks"),
            StructuredTool.from_function(coroutine=delete_task, name="delete_task"),
            StructuredTool.from_function(coroutine=ask_user, name="ask_user"),
        ]
        return tools


def _require_chat(ctx: _TurnContext) -> str:
    if ctx.chat_id is None:
        raise RuntimeError("surface tool invoked outside a converse() turn")
    return ctx.chat_id


def _last_text(result: dict[str, Any]) -> str:
    for msg in reversed(result.get("messages", [])):
        content = getattr(msg, "content", None)
        role = getattr(msg, "type", None) or getattr(msg, "role", None)
        if role in ("ai", "assistant") and isinstance(content, str) and content.strip():
            return content
    # Fall back to the last textual message of any kind.
    for msg in reversed(result.get("messages", [])):
        content = getattr(msg, "content", None)
        if isinstance(content, str) and content.strip():
            return content
    return ""


def _summarize_booking(b: Booking) -> str:
    state = _lifecycle_label(b.lifecycle)
    return f"{b.booking_id} — {b.hotel.hotel_name} ({state})"


def _lifecycle_label(lifecycle: BookingLifecycle) -> str:
    # Human-readable progress for the chat; cancelled is surfaced as a terminal outcome.
    labels = {
        BookingLifecycle.CANCELLED: "cancelled",
        BookingLifecycle.REPORT_SENT: "report sent",
        BookingLifecycle.AWAITING_REPLY: "waiting for the hotel",
        BookingLifecycle.IN_CONVERSATION: "talking to the hotel",
        BookingLifecycle.CONTACT_READY: "preparing to contact the hotel",
    }
    return labels.get(lifecycle, lifecycle.value)
