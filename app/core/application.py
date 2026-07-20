import logging

logger = logging.getLogger(__name__)


class Application:
    """Process-wide state and service lifecycle.

    Holds long-lived clients (the LLM provider, and later retrieval) once they
    exist. For now it only tracks start/stop so the FastAPI lifespan has one
    wiring point to grow into.
    """

    def __init__(self) -> None:
        self.started = False

    async def start(self) -> None:
        if self.started:
            return
        logger.info("Starting application")
        # TODO: initialize services here as they are added.
        self.started = True
        logger.info("Application started")

    async def stop(self) -> None:
        if not self.started:
            return
        logger.info("Stopping application")
        # TODO: close services here as they are added.
        self.started = False
        logger.info("Application stopped")


_api_app = Application()


async def init_api_app() -> Application:
    if not _api_app.started:
        await _api_app.start()
    return _api_app
