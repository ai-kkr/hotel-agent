"""Custom SQLAlchemy column types."""

from __future__ import annotations

from sqlalchemy import JSON, TypeDecorator

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
