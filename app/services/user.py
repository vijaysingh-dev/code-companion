import logging
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.models.tables import User

logger = logging.getLogger(__name__)

# Admin-chosen handle: 2-64 chars, alphanumeric plus '-'/'_', starting alphanumeric.
_HANDLE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{1,63}$")


class UserService:
    """CRUD for users, over a caller-supplied async session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: str, name: str, email: str | None = None) -> User:
        if not _HANDLE_RE.match(user_id):
            raise ValidationError(
                "user id must be 2-64 chars: letters, digits, '-' or '_', starting alphanumeric",
                details={"user_id": user_id},
            )
        user = User(id=user_id, name=name, email=email)
        self._session.add(user)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            logger.warning("User create conflict (id=%s, email=%s)", user_id, email)
            raise ValidationError(
                "a user with this id or email already exists",
                details={"user_id": user_id, "email": email},
            ) from exc
        await self._session.refresh(user)
        logger.info("Created user %s (%s)", user.id, user.name)
        return user

    async def get(self, user_id: str) -> User:
        user = await self._session.get(User, user_id)
        if user is None:
            raise ResourceNotFoundError("User", details={"user_id": user_id})
        return user

    async def list_all(self) -> list[User]:
        result = await self._session.execute(select(User).order_by(User.created_at))
        return list(result.scalars().all())
