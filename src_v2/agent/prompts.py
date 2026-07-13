from pathlib import Path

from langchain_core.messages import SystemMessage

__all__ = [
    "SYSTEM_LETTER_TO_HOTEL",
    "SYSTEM_MAIN",
]

_root = Path(__file__).parent

SYSTEM_MAIN = SystemMessage((_root / "prompts/system_main.md").read_text())
SYSTEM_LETTER_TO_HOTEL = SystemMessage((_root / "prompts/system_letter_to_hotel.md").read_text())
