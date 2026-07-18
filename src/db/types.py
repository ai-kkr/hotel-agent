"""Custom SQLAlchemy column types."""

from __future__ import annotations

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB

from src.integrations.mailtrap.mailtrap_inbound.models import MessageDetails


class MessageDetailsType(TypeDecorator):
    """Column type that transparently (de)serializes a :class:`MessageDetails`.

    Stored as native JSON (``JSONB`` on Postgres, ``JSON`` elsewhere). The Python side always sees
    a ``MessageDetails`` instance; conversion uses its ``to_dict``/``from_dict`` (the generated
    attrs model), which omit ``Unset`` fields and round-trip cleanly.
    """

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        # Python -> DB: accept a MessageDetails (or a bare dict / None) and hand SQLAlchemy a
        # JSON-serializable dict.
        if value is None or isinstance(value, dict):
            return value
        return value.to_dict()

    def process_result_value(self, value, dialect):
        # DB -> Python: the JSON impl already parsed the column into a dict; rebuild the model.
        if value is None:
            return None
        return MessageDetails.from_dict(value)


class StateType(TypeDecorator):
    """Column type that persists an agent state dict (:class:`src.agent.state.EmailState`) as native
    JSON, transparently converting the only non-JSON field — ``messages`` (langchain
    ``BaseMessage`` objects) — via langchain's own ``messages_to_dict`` / ``messages_from_dict``.

    All other ``EmailState`` fields are already JSON-native (str / list[str] / bool / int / None).
    Stored as ``JSONB`` on Postgres (binary, indexable) and ``JSON`` on SQLite (tests).

    The Python side always sees a state dict whose ``messages`` are live ``BaseMessage`` objects;
    on the DB side ``messages`` is the langchain ``[{"type": ..., "data": {...}}]`` shape.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        # JSONB on Postgres, plain JSON elsewhere (e.g. SQLite in tests).
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        # Python -> DB: hand SQLAlchemy a JSON-serializable dict. Only ``messages`` needs work; if
        # it's already a list of dicts (pre-serialized) leave it untouched.
        from langchain_core.messages import BaseMessage, messages_to_dict

        if value is None:
            return None
        out = dict(value)
        msgs = out.get("messages")
        if msgs and isinstance(msgs[0], BaseMessage):
            out["messages"] = messages_to_dict(msgs)
        return out

    def process_result_value(self, value, dialect):
        # DB -> Python: the JSON impl parsed the column into a dict; revive ``messages`` objects.
        from langchain_core.messages import messages_from_dict

        if value is None:
            return None
        out = dict(value)
        if out.get("messages"):
            out["messages"] = messages_from_dict(out["messages"])
        return out
