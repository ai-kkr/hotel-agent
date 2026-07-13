"""Serializable runtime context for the hotel-conversation agent.

Per the project's "context must be serializable" constraint, this carries only plain data. Every
non-serializable dependency (chat model, Tavily client, Mailtrap gateway, …) is fetched from the
application context via :func:`src.context.get_context` directly inside the tool that needs it,
not stored here.
"""

from typing import TypedDict

__all__ = ["EmailContext"]


class EmailContext(TypedDict):
    #: Verified Mailtrap sending address used as ``From`` (must be on a verified sending domain).
    from_email: str | None
    #: Client's inbound inbox address; set as ``Reply-To`` so hotel replies land back in the
    #: client's inbox and the inbound webhook can route them to the agent.
    reply_to: str | None
    #: Client's own email; in ``is_dev`` outbound is redirected here instead of the real hotel.
    user_email: str | None
    #: Client id, to bind the sent email record (``outbound_emails``) for reply matching.
    client_id: int | None
