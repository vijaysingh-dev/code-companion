from fastapi import APIRouter

from app.api import chat, health

# Single, unversioned API router. Add new resource routers here.
api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(chat.router)
