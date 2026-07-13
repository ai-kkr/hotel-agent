from infrastructure.config import get_settings
from src_v2.integrations.mailtrap.mailtrap_inbound import AuthenticatedClient
from src_v2.integrations.mailtrap.mailtrap_inbound.api.inboxes import create_inbound_inbox
from src_v2.integrations.mailtrap.mailtrap_inbound.api.messages import get_inbound_message
from src_v2.integrations.mailtrap.mailtrap_inbound.models.inbox import Inbox
from src_v2.integrations.mailtrap.mailtrap_inbound.models.inbox_input import InboxInput
from src_v2.integrations.mailtrap.mailtrap_inbound.models.message_details import MessageDetails
from src_v2.integrations.mailtrap.mailtrap_send.api.send_email import (
    send_email as send_email_api,
)
from src_v2.integrations.mailtrap.mailtrap_send.client import (
    AuthenticatedClient as SendAuthenticatedClient,
)
from src_v2.integrations.mailtrap.mailtrap_send.models.address import Address
from src_v2.integrations.mailtrap.mailtrap_send.models.html_only import HTMLOnly
from src_v2.integrations.mailtrap.mailtrap_send.models.sent_response import SentResponse
from src_v2.integrations.mailtrap.mailtrap_send.models.text_and_html import TextAndHTML
from src_v2.integrations.mailtrap.mailtrap_send.models.text_only import TextOnly

SEND_BASE_URL = "https://send.api.mailtrap.io"


class MailtrapClient:
    def __init__(self, client: AuthenticatedClient):
        self.client = client
        # Separate client for outbound sending — it lives on a different host (send.api) than
        # inbound, but uses the same API token. Generated httpx client, fully async.
        self._send_client = SendAuthenticatedClient(
            base_url=SEND_BASE_URL,
            token=client.token,
        )

    async def send(
        self,
        *,
        sender: str,
        to: list[str],
        subject: str,
        text: str | None = None,
        html: str | None = None,
        sender_name: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        reply_to: str | None = None,
        category: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> SentResponse:
        """Send a transactional email via Mailtrap (``POST send.api.mailtrap.io/api/send``).

        Picks the request variant by which body parts are present: ``TextAndHTML`` if both,
        ``TextOnly`` / ``HTMLOnly`` otherwise. At least one of ``text``/``html`` is required.
        ``headers`` sets custom SMTP headers (e.g. ``In-Reply-To``/``References`` for threading).
        Raises ``RuntimeError`` if Mailtrap returns an error response.
        """
        from_addr = Address(email=sender, name=sender_name) if sender_name else Address(email=sender)
        common: dict = {
            "from_": from_addr,
            "to": [Address(email=addr) for addr in to],
            "subject": subject,
        }
        if cc:
            common["cc"] = [Address(email=addr) for addr in cc]
        if bcc:
            common["bcc"] = [Address(email=addr) for addr in bcc]
        if reply_to:
            common["reply_to"] = Address(email=reply_to)
        if category:
            common["category"] = category
        if headers:
            common["headers"] = headers

        if text and html:
            body = TextAndHTML(text=text, html=html, **common)
        elif text:
            body = TextOnly(text=text, **common)
        elif html:
            body = HTMLOnly(html=html, **common)
        else:
            raise ValueError("send() requires at least one of text or html")

        response = await send_email_api.asyncio(client=self._send_client, body=body)
        if isinstance(response, SentResponse):
            return response
        raise RuntimeError(f"Mailtrap send failed: {response}")

    async def get_message(self, message_id: str, inbox_id: int) -> MessageDetails:

        ret = await get_inbound_message.asyncio(
            inbox_id=inbox_id,
            id=message_id,
            client=self.client,
        )
        assert isinstance(ret, MessageDetails), f"Expected MessageDetails, got {type(ret)}: {ret}"
        return ret

    async def provision_inbox(self, name: str) -> Inbox:
        settings = get_settings()
        inbox = await create_inbound_inbox.asyncio(
            folder_id=settings.mailtrap_inbox_id,
            client=self.client,
            body=InboxInput(name=name),
        )
        if isinstance(inbox, Inbox):
            return inbox  # address отдаём отелю; (folder_id, inbox.id) храним
        raise RuntimeError(f"Failed to provision inbox: {inbox}")
