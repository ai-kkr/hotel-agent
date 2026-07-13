from typing import Literal

from pydantic import BaseModel

__all__ = ["MessageText"]


class MessageText(BaseModel):
    """A chunk of text streamed from the agent to the user (custom stream mode)."""

    text: str
    is_confirm: bool = False
    type: Literal["message_text"] = "message_text"
