import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.application import init_api_app
from app.core.config import settings
from app.core.logging import setup_logging
from app.middleware.error_handler import setup_exception_handlers
from app.middleware.logging import LoggingMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.app = await init_api_app()
    try:
        yield
    finally:
        await app.state.app.stop()


def create_application() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.DESCRIPTION,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)

    setup_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_PREFIX)

    return app


app = create_application()
