import logging
from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.application import Application
from app.services.chat import ChatService

logger = logging.getLogger(__name__)


def get_app(request: Request) -> Application:
    return cast(Application, request.app.state.app)


async def get_db(app: Annotated[Application, Depends(get_app)]) -> AsyncIterator[AsyncSession]:
    async with app.sessionmaker() as session:
        yield session


def get_chat_service(app: Annotated[Application, Depends(get_app)]) -> ChatService:
    """A ChatService over the app-wide DB + HTTP client (it builds providers per request)."""
    return ChatService(app.sessionmaker, app.client)
