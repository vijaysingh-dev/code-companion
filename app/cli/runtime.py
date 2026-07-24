import asyncio
import logging
from collections.abc import Awaitable, Callable

from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from app.cli.migrate import alembic_config
from app.core.application import Application, get_cli_app

logger = logging.getLogger(__name__)

_app: Application | None = None


def get_app() -> Application:
    if _app is None:
        raise RuntimeError("App not initialized; call inside run_async()")
    return _app


def _current_revision(conn: Connection) -> str | None:
    return MigrationContext.configure(conn).get_current_revision()


async def _ensure_migrated(engine: AsyncEngine) -> None:
    """Raise unless the DB is at the latest migration (matches the neo4j-era guard)."""
    async with engine.connect() as conn:
        current = await conn.run_sync(_current_revision)
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    if current != head:
        raise RuntimeError("Database not migrated. Run `python -m app.cli.main migrate` first.")


def run_async(func: Callable[[], Awaitable[None]], require_migration: bool = True) -> None:
    """Start a CLI-mode Application, run `func`, then stop.

    `require_migration` (default True) fails fast if the schema is behind head; the
    `migrate` command runs outside this (it's what brings the schema up to date).
    """

    async def runner() -> None:
        global _app
        _app = get_cli_app()
        await _app.start()
        if require_migration:
            await _ensure_migrated(_app.engine)
        try:
            await func()
        finally:
            await _app.stop()
            _app = None

    asyncio.run(runner())
