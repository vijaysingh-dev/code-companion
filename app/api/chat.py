import logging

from fastapi import APIRouter

from app.models.schema import ChatRequest, ChatResponse
from app.services.chat import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

chat_service = ChatService()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    answer = await chat_service.answer(request.message, context=request.context)
    return ChatResponse(content=answer)
