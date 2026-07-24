from fastapi import APIRouter

from app.api import chat, health, models, sessions

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
