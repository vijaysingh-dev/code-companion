import logging
from typing import cast

from fastapi import Request

from app.core.application import Application

logger = logging.getLogger(__name__)


def get_app(request: Request) -> Application:
    return cast(Application, request.app.state.app)
