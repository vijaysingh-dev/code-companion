import logging

from fastapi import APIRouter

from app.core.config import settings
from app.models.schema import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", version=settings.APP_VERSION)
