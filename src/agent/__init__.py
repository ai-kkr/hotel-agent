"""Hotel-conversation ReAct agent.

A hand-built :class:`langgraph.graph.StateGraph` agent (model + tools nodes, run under Temporal)
that handles the full forwarded-email scenario end to end: discover the hotel contact email,
clarify the user's wishes, and either send them to the hotel or cancel with a reason.
"""

from .agent import build_email_agent
from .context import EmailContext
from .state import EmailState

__all__ = ["EmailContext", "EmailState", "build_email_agent"]
