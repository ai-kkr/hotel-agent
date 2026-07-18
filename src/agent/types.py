from typing import Literal

from langchain_core.utils.uuid import uuid7
from pydantic import BaseModel, Field

__all__ = ["MessageText"]


class MessageText(BaseModel):
    """A chunk of text streamed from the agent to the user (custom stream mode)."""

    text: str
    id: str = Field(default_factory=lambda: str(uuid7()))
    is_confirm: bool = False
    type: Literal["message_text"] = "message_text"
