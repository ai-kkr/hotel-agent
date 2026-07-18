from pydantic import BaseModel
from temporalio import workflow

from src.agent.state import EmailState

with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel


class RunInput(BaseModel):
    """Input to :class:`AgentWorkflow`: the turn's message update plus routing/identity.

    ``state_update`` is an optional partial-state merge applied to the loaded state before the turn
    runs — used by the webhook to inject a hotel reply's ``Message-ID``/subject (so ``reply_to_hotel``
    can thread the next email) without a separate state-write call. ``None`` for a plain turn.
    """

    state: EmailState
    thread_id: str
    client_id: int
    telegram_id: int
    client_email: str | None = None
    client_inbox: str | None = None
    from_email: str | None = None
    state_update: EmailState | None = None

