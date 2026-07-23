import logging

from fastapi import APIRouter

from app.models.schema import ModelsResponse
from app.services import catalog

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """Main-tier models the client may choose, for the configured provider."""
    return catalog.list_models()
