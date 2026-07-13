from typing import Annotated

import fastapi
import mailtrap as mt
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.config import Settings, get_settings
from src_v2.context import AppContext
from src_v2.db.session import session_context

__all__ = ["AppSession", "AppSettings", "verify_mailtrap_signature"]


async def _get_settings():
    return get_settings()


type AppSettings = Annotated[Settings, fastapi.Depends(_get_settings)]


async def verify_mailtrap_signature(request: fastapi.Request, settings: AppSettings) -> None:
    """FastAPI dependency: verify the Mailtrap-Signature header against the raw body.

    HMAC must be computed over the **raw** request body, so we read it before FastAPI parses
    the JSON. The body is cached on the request, so the handler's ``payload: dict`` still works.
    """
    signing_secret = settings.mailtrap_signing_secret
    signature = request.headers.get("Mailtrap-Signature", "")
    raw_body = await request.body()
    if not mt.verify_signature(raw_body, signature, signing_secret):
        raise fastapi.HTTPException(status_code=401, detail="Invalid Mailtrap signature")


async def _get_session(ctx: AppContext):
    async with session_context(ctx.session_factory) as session:
        yield session


type AppSession = Annotated[AsyncSession, Depends(_get_session)]
