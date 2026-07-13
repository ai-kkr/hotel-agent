from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import SystemMessage

__all__ = [
    "SYSTEM_CLASSIFY_USER_REPLY",
    "SYSTEM_EXTRACT_EMAIL",
    "SYSTEM_HOTEL_CONVERSATION",
    "SYSTEM_LETTER_TO_HOTEL",
    "SYSTEM_MESSAGE",
    "SYSTEM_SEARCH_EMAIL",
    "SYSTEM_USER_INTENTION",
]
_root = Path(__file__).parent

env = Environment(loader=FileSystemLoader(_root / "prompts"), autoescape=True)
SYSTEM_MESSAGE = SystemMessage((_root / "prompts/system_main.md").read_text())
SYSTEM_EXTRACT_EMAIL = SystemMessage((_root / "prompts/system_extract_email.md").read_text())
SYSTEM_SEARCH_EMAIL = SystemMessage((_root / "prompts/system_search_email.md").read_text())
SYSTEM_USER_INTENTION = SystemMessage((_root / "prompts/system_get_user_intention.md").read_text())
SYSTEM_CLASSIFY_USER_REPLY = SystemMessage(
    (_root / "prompts/system_classify_user_reply.md").read_text()
)
SYSTEM_HOTEL_CONVERSATION = SystemMessage(
    (_root / "prompts/system_hotel_conversation.md").read_text()
)
SYSTEM_LETTER_TO_HOTEL = SystemMessage((_root / "prompts/system_letter_to_hotel.md").read_text())
