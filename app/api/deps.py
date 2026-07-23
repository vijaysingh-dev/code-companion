import logging
from typing import Annotated, cast

from fastapi import Depends, Request

from app.core.application import Application
from app.llm.provider import get_provider
from app.services.chat import ChatService

logger = logging.getLogger(__name__)


def get_app(request: Request) -> Application:
    return cast(Application, request.app.state.app)


def get_chat_service(app: Annotated[Application, Depends(get_app)]) -> ChatService:
    """Build a ChatService whose provider shares the app-wide HTTP client."""
    return ChatService(get_provider("main", client=app.client))
