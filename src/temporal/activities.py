from pydantic import BaseModel
from temporalio import activity

from src.agent.state import EmailState
from src.context import get_context
from src.db.repositories import ClientRepository
from src.db.session import session_context


class SaveStateInput(BaseModel):
    client_id: int
    state: EmailState


@activity.defn
async def load_state(client_id: int) -> EmailState | None:
    """Load the persisted agent state for a client, or ``None`` if none is stored yet."""
    ctx = get_context()
    async with session_context(ctx.session_factory) as session:
        return await ClientRepository(session).get_state_by_client_id(client_id=client_id)


@activity.defn
async def save_state(input: SaveStateInput) -> None:
    """Persist the agent state for a client (upsert — ``client_id`` is the ``states`` primary key)."""
    ctx = get_context()
    async with session_context(ctx.session_factory) as session:
        await ClientRepository(session).set_state_by_client_id(
            client_id=input.client_id,
            state=input.state,
        )
