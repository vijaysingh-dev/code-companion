import logging

import httpx

logger = logging.getLogger(__name__)


class Application:
    """Process-wide state and service lifecycle.

    Owns the shared async HTTP client used by outbound integrations (the LLM
    providers today, retrieval later). Kept provider-agnostic so `core` stays
    generic — feature code builds providers on top of `client`. One wiring point
    for the FastAPI lifespan to grow into.
    """

    def __init__(self) -> None:
        self.started = False
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Application not started")
        return self._client

    async def start(self) -> None:
        if self.started:
            return
        logger.info("Starting application")
        self._client = httpx.AsyncClient(timeout=600.0)
        self.started = True
        logger.info("Application started")

    async def stop(self) -> None:
        if not self.started:
            return
        logger.info("Stopping application")
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self.started = False
        logger.info("Application stopped")


_api_app = Application()


async def init_api_app() -> Application:
    if not _api_app.started:
        await _api_app.start()
    return _api_app
