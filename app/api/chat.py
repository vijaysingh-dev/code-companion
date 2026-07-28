import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.auth import authenticated
from app.api.deps import get_chat_service
from app.core.constants import StreamEventType
from app.models.response import StreamEvent
from app.models.schema import ChatRequest
from app.services.chat import ChatService

logger = logging.getLogger(__name__)

router = APIRouter()


def _sse(event: StreamEvent) -> str:
    return f"event: {event.type.value}\ndata: {event.model_dump_json(exclude_none=True)}\n\n"


@router.post("")
@authenticated
async def chat(
    request: Request,
    body: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    # prepare_turn validates the session (404) and model (422) and persists the user turn
    # before any bytes are streamed, so those stay clean HTTP errors.
    resolved, messages, needs_title = await service.prepare_turn(
        request.state.user_id, body.session_id, body.message, body.provider, body.model
    )

    async def frames() -> AsyncIterator[str]:
        try:
            async for event in service.stream_turn(
                body.session_id, resolved, messages, body.context, body.effort, generate_title=needs_title
            ):
                yield _sse(event)
        except Exception as exc:  # noqa: BLE001 - headers already sent; surface as an SSE error, not a 500
            logger.exception("chat stream failed")
            yield _sse(StreamEvent(type=StreamEventType.ERROR, error=str(exc)))
        yield _sse(StreamEvent(type=StreamEventType.DONE))

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
