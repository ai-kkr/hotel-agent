"""Email-extraction graph package.

Parses a forwarded booking confirmation, discovers the hotel's contact email (searching the
web if needed), and collects the user's wishes for the outgoing message. Re-exports the
public surface so callers can keep importing from the package root::

    from src_v2.agent.nodes.email_extractor import get_email_graph, ExtractedBookingSchema
"""

from .graph import get_email_graph, workflow
from .nodes import get_user_intention_loop
from .schemas import ExtractedBookingSchema, UserIntentionSchema, UserReplyClassification
from .state import (
    EmailInputState,
    EmailOutputState,
    EmailState,
    EmailToHotelInputState,
    EmailToHotelOutputState,
)

__all__ = [
    "ExtractedBookingSchema",
    "UserIntentionSchema",
    "UserReplyClassification",
    "EmailInputState",
    "EmailOutputState",
    "EmailState",
    "EmailToHotelInputState",
    "EmailToHotelOutputState",
    "get_email_graph",
    "get_user_intention_loop",
    "workflow",
]
