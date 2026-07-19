import secrets

from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.state import EmailState
from src.context import AppContext, get_context
from src.integrations.mailtrap.mailtrap_inbound.models import MessageDetails

from .models import ClientORM as Client
from .models import ForwardedEmailORM, OutboundEmailORM, ScheduledTaskORM, StateORM


class DuplicateForwardedEmailError(Exception):
    """Raised when trying to add a forwarded email that already exists in the database."""


class ClientRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    @property
    def ctx(self) -> AppContext:
        return get_context()

    async def get_client_by_telegram_id(self, telegram_id: int) -> Client | None:
        result = await self.db_session.execute(
            select(Client).filter(Client.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_client_by_email(self, email: str) -> Client | None:
        result = await self.db_session.execute(select(Client).filter(Client.email == email))
        return result.scalar_one_or_none()

    async def get_client_by_inbox(self, inbox: str) -> Client | None:
        result = await self.db_session.execute(select(Client).filter(Client.inbox == inbox))
        return result.scalar_one_or_none()

    async def get_client_by_inbox_id(self, inbox_id: int) -> Client | None:
        result = await self.db_session.execute(select(Client).filter(Client.inbox_id == inbox_id))
        return result.scalar_one_or_none()

    async def add_client(
        self,
        telegram_id: int | None = None,
        email: str | None = None,
    ) -> Client:
        inbox = await self.ctx.mailtrap_client.provision_inbox(
            name=f"client-{secrets.token_urlsafe(9)}",
        )
        client = Client(
            telegram_id=telegram_id,
            email=email,
            inbox=inbox.address,
            inbox_id=inbox.id,
        )
        self.db_session.add(client)
        return client

    async def add_forwarded_email(self, client_id: int, data: MessageDetails) -> ForwardedEmailORM:
        # check if the email has already been forwarded to avoid duplicates
        result = await self.db_session.execute(
            select(ForwardedEmailORM).filter(
                ForwardedEmailORM.message_id == data.message_id,
                ForwardedEmailORM.client_id == client_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            raise DuplicateForwardedEmailError()

        forwarded_email = ForwardedEmailORM(
            client_id=client_id,
            data=data,
            id=data.id,
            message_id=data.message_id,
        )
        self.db_session.add(forwarded_email)
        return forwarded_email

    async def add_outbound(
        self,
        *,
        message_id: str,
        client_id: int,
        subject: str | None = None,
        in_reply_to: str | None = None,
    ) -> OutboundEmailORM:
        """Record an outbound email so the webhook can later match a hotel reply by In-Reply-To."""
        outbound = OutboundEmailORM(
            message_id=message_id,
            client_id=client_id,
            subject=subject,
            in_reply_to=in_reply_to,
        )
        self.db_session.add(outbound)
        return outbound

    async def get_outbound_by_message_id(self, message_id: str) -> OutboundEmailORM | None:
        result = await self.db_session.execute(
            select(OutboundEmailORM).filter(OutboundEmailORM.message_id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_state_by_client_id(self, client_id: int) -> EmailState | None:
        """Return the persisted agent state for a client, or ``None`` if none is stored yet.

        The ``state`` column is native JSON (``JSONB`` on Postgres), so SQLAlchemy already parses it
        into a plain ``dict`` — no manual deserialization here.
        """
        result = await self.db_session.execute(
            select(StateORM.state).filter(StateORM.client_id == client_id)
        )
        return result.scalar_one_or_none()

    async def set_state_by_client_id(self, client_id: int, state: EmailState) -> None:
        """Persist the agent state for a client, inserting or replacing the single row.

        ``client_id`` is the primary key of ``states``, so this is an upsert. Load-or-create keeps
        it dialect-agnostic (works on SQLite for tests); ``updated_at`` refreshes automatically via
        the column's ``onupdate``.
        """
        result = await self.db_session.execute(
            select(StateORM).filter(StateORM.client_id == client_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            self.db_session.add(StateORM(client_id=client_id, state=state))
        else:
            row.state = state

    async def delete_state_by_client_id(self, client_id: int) -> None:
        """Delete the persisted agent state for a client, if any.

        No-op when there is no row (e.g. the client never had a turn). The caller must commit the
        session for the delete to take effect — same as the other mutating methods here.
        """
        result = await self.db_session.execute(
            select(StateORM).filter(StateORM.client_id == client_id)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self.db_session.delete(row)

    async def get_timezones(self, client_id: int) -> tuple[str | None, str | None]:
        """Cheaply read the client's scheduling timezones (``home_timezone``, ``trip_timezone``)
        straight out of the ``states`` JSONB — without loading the full state (no message history).

        The ``state`` column is wrapped in :class:`StateType` (a ``TypeDecorator``), whose
        comparator doesn't expose ``astext`` — so we ``cast`` it to ``JSONB`` first, then use the
        ``->>`` text-extraction the JSON comparator provides. Returns ``(None, None)`` when there's
        no state row or the fields aren't set yet.
        """
        result = await self.db_session.execute(
            select(
                cast(StateORM.state, JSONB)["home_timezone"].astext,
                cast(StateORM.state, JSONB)["trip_timezone"].astext,
            ).where(StateORM.client_id == client_id)
        )
        row = result.one_or_none()
        if row is None:
            return (None, None)
        return (row[0], row[1])


class ScheduledTaskRepository:
    """CRUD over the :class:`ScheduledTaskORM` catalog — the agent's cheap list/existence index for a
    client's scheduled tasks (Temporal Schedules can't be filtered server-side, so we index them).

    The caller commits the session (via ``session_context``); these methods only stage changes.
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def list_by_client(self, client_id: int) -> list[ScheduledTaskORM]:
        """All catalog rows for ``client_id`` (ordered for stable listing)."""
        result = await self.db_session.execute(
            select(ScheduledTaskORM)
            .where(ScheduledTaskORM.client_id == client_id)
            .order_by(ScheduledTaskORM.created_at, ScheduledTaskORM.task_key)
        )
        return list(result.scalars().all())

    async def keys_for_client(self, client_id: int) -> list[str]:
        """Just the ``task_key``s for ``client_id`` — for existence checks / error messages."""
        result = await self.db_session.execute(
            select(ScheduledTaskORM.task_key).where(ScheduledTaskORM.client_id == client_id)
        )
        return list(result.scalars().all())

    async def get(self, client_id: int, task_key: str) -> ScheduledTaskORM | None:
        result = await self.db_session.execute(
            select(ScheduledTaskORM).where(
                ScheduledTaskORM.client_id == client_id,
                ScheduledTaskORM.task_key == task_key,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        client_id: int,
        task_key: str,
        description: str,
        spec_summary: str,
        paused: bool,
        remaining: int | None,
    ) -> None:
        """Insert or fully replace a catalog row (the display fields)."""
        row = await self.get(client_id, task_key)
        if row is None:
            self.db_session.add(
                ScheduledTaskORM(
                    client_id=client_id,
                    task_key=task_key,
                    description=description,
                    spec_summary=spec_summary,
                    paused=paused,
                    remaining=remaining,
                )
            )
        else:
            row.description = description
            row.spec_summary = spec_summary
            row.paused = paused
            row.remaining = remaining

    async def delete(self, client_id: int, task_key: str) -> None:
        """Remove a catalog row (no-op if absent)."""
        row = await self.get(client_id, task_key)
        if row is not None:
            await self.db_session.delete(row)
