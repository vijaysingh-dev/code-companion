import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import utc_now
from app.core.exceptions import ResourceNotFoundError
from app.models.message import Message
from app.models.tables import ChatSession, SessionMessage
from app.models.usage import Usage

logger = logging.getLogger(__name__)


class SessionService:
    """Conversation sessions and their persisted messages, over an async session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: str, provider: str, model: str, title: str | None = None) -> ChatSession:
        row = ChatSession(user_id=user_id, provider=provider, model=model, title=title)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        logger.info("Created session %s for user %s", row.id, user_id)
        return row

    async def get(self, user_id: str, session_id: str) -> ChatSession:
        row = await self._session.get(ChatSession, session_id)
        if row is None or row.user_id != user_id:
            raise ResourceNotFoundError("ChatSession", details={"session_id": session_id})
        return row

    async def update_title(self, user_id: str, session_id: str, title: str) -> ChatSession:
        """Set a session's title, scoped to its owner (404s otherwise via get)."""
        row = await self.get(user_id, session_id)
        row.title = title
        await self._session.commit()
        await self._session.refresh(row)
        logger.info("Updated title for session %s", session_id)
        return row

    async def set_title(self, session_id: str, title: str) -> None:
        """Internal, unscoped title write (owner already verified upstream)."""
        row = await self._session.get(ChatSession, session_id)
        if row is not None:
            row.title = title
            await self._session.commit()

    async def list_all(self, user_id: str) -> list[ChatSession]:
        result = await self._session.execute(
            select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, user_id: str, session_id: str) -> None:
        row = await self.get(user_id, session_id)
        await self._session.execute(delete(SessionMessage).where(SessionMessage.session_id == row.id))
        await self._session.delete(row)
        await self._session.commit()
        logger.info("Deleted session %s", session_id)

    async def history(self, session_id: str) -> list[Message]:
        """The session's messages, oldest first, as domain Messages."""
        result = await self._session.execute(
            select(SessionMessage).where(SessionMessage.session_id == session_id).order_by(SessionMessage.id)
        )
        return [Message.model_validate({"role": row.role, "content": row.content}) for row in result.scalars().all()]

    async def rows(self, session_id: str) -> list[SessionMessage]:
        result = await self._session.execute(
            select(SessionMessage).where(SessionMessage.session_id == session_id).order_by(SessionMessage.id)
        )
        return list(result.scalars().all())

    async def add_message(self, session_id: str, message: Message, usage: Usage | None = None) -> None:
        self._session.add(
            SessionMessage(
                session_id=session_id,
                role=message.role.value,
                content=[part.model_dump(mode="json") for part in message.content],
                usage=usage.model_dump(mode="json") if usage else None,
            )
        )
        await self._session.commit()

    async def touch(self, session_id: str, provider: str, model: str) -> None:
        """Record the model used this turn and bump the session's recency."""
        row = await self._session.get(ChatSession, session_id)
        if row is not None:
            row.provider, row.model, row.updated_at = provider, model, utc_now()
            await self._session.commit()
