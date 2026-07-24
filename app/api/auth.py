import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from fastapi import Request

from app.core.exceptions import AuthenticationError
from app.core.security import verify_token

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("missing or malformed Authorization header")
    return token


def authenticated(func: F) -> F:
    """Endpoint decorator: verify the bearer token and stash the user id on request.state.

    A temporary bridge until an AuthMiddleware covers all protected routes (it will
    keep the same `request.state.user_id` contract). The decorated endpoint must
    declare `request: Request` and reads the caller via `request.state.user_id`.
    A missing/invalid/expired token raises AuthenticationError → 401.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = next((v for v in (*args, *kwargs.values()) if isinstance(v, Request)), None)
        if request is None:
            raise RuntimeError("@authenticated requires a `request: Request` parameter")
        request.state.user_id = verify_token(_bearer_token(request))
        logger.debug("Authenticated request for user %s", request.state.user_id)
        return await func(*args, **kwargs)

    return cast(F, wrapper)
