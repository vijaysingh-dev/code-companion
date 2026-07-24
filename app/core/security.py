import logging
from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.constants import utc_now
from app.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

_ALGORITHM = "HS256"


def create_token(user_id: str) -> str:
    """Sign a stateless access token carrying `user_id` in `sub`, expiring in TOKEN_TTL_DAYS."""
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set; cannot sign tokens")
    curr_time = utc_now()
    payload = {
        "sub": user_id,
        "iat": curr_time,
        "exp": curr_time + timedelta(days=settings.TOKEN_TTL_DAYS),
    }
    logger.info("\nIssued token for user %s (ttl=%dd)", user_id, settings.TOKEN_TTL_DAYS)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def verify_token(token: str) -> str:
    """Verify signature + expiry and return the `user_id`, or raise AuthenticationError (401)."""
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set; cannot verify tokens")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        logger.warning("Rejected token: %s", exc)
        raise AuthenticationError("invalid or expired token") from exc
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise AuthenticationError("token is missing a subject")
    return user_id
