import logging
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import utc_now
from app.core.db import Base

logger = logging.getLogger(__name__)


class User(Base):
    """A developer who can be issued access tokens. Token-only identity — no password.

    `id` is an admin-chosen handle (e.g. "alice") supplied at creation, not generated.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now())
