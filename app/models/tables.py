import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import utc_now
from app.core.db import Base

logger = logging.getLogger(__name__)


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    """A developer who can be issued access tokens. Token-only identity — no password.

    `id` is an admin-chosen handle (e.g. "alice") supplied at creation, not generated.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Session(Base):
    """A conversation thread owned by a user. Holds the currently selected model."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(128))
    title: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class SessionMessage(Base):
    """One turn in a session. `content` is the JSON-serialized list of message parts."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    usage: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
