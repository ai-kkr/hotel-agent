"""Hotel-conversation ReAct agent.

A single :func:`langchain.agents.create_agent`-based agent that handles the full forwarded-email
scenario end to end: discover the hotel contact email, clarify the user's wishes, and either send
them to the hotel or cancel with a reason.
"""

from .agent import build_email_agent
from .context import EmailContext
from .state import EmailState

__all__ = ["EmailContext", "EmailState", "build_email_agent"]
