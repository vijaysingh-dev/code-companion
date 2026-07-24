import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.constants import AppMode
from app.core.db import create_engine, create_sessionmaker

logger = logging.getLogger(__name__)


class Application:
    """Process-wide state and service lifecycle, shared by the API and the CLI.

    Owns the DB engine/sessionmaker (both modes) and the outbound HTTP client used
    by LLM providers (APP mode only — the CLI does no LLM I/O). Kept generic so
    `core` stays reusable; feature code builds on `sessionmaker` / `client`.
    """

    def __init__(self, mode: AppMode) -> None:
        self.mode = mode
        self.started = False
        self._client: httpx.AsyncClient | None = None
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("HTTP client unavailable (CLI mode, or application not started)")
        return self._client

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("Application not started")
        return self._engine

    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._sessionmaker is None:
            raise RuntimeError("Application not started")
        return self._sessionmaker

    async def start(self) -> None:
        if self.started:
            return
        logger.info("Starting application (mode=%s)", self.mode.value)
        self._engine = create_engine()
        self._sessionmaker = create_sessionmaker(self._engine)
        if self.mode is AppMode.APP:
            self._client = httpx.AsyncClient(timeout=600.0)
        self.started = True
        logger.info("Application started\n")

    async def stop(self) -> None:
        if not self.started:
            return
        logger.info("\nStopping application")
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
        self._sessionmaker = None
        self.started = False
        logger.info("Application stopped")


_api_app = Application(AppMode.APP)


async def init_api_app() -> Application:
    if not _api_app.started:
        await _api_app.start()
    return _api_app


def get_cli_app() -> Application:
    """A fresh, unstarted CLI-mode Application (the caller runs start/stop)."""
    return Application(AppMode.CLI)
