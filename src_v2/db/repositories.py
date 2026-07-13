import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src_v2.context import AppContext, get_context
from src_v2.integrations.mailtrap.mailtrap_inbound.models import MessageDetails

from .models import ClientORM as Client
from .models import ForwardedEmailORM
from .models import OutboundEmailORM


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
