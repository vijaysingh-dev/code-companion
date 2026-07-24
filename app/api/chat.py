import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.auth import authenticated
from app.api.deps import get_chat_service
from app.core.constants import StreamEventType
from app.models.response import StreamEvent
from app.models.schema import ChatRequest
from app.services import catalog
from app.services.chat import ChatService

logger = logging.getLogger(__name__)

router = APIRouter()


def _sse(event: StreamEvent) -> str:
    """Serialize a StreamEvent as an SSE frame (`event:` name + JSON `data:`)."""
    return f"event: {event.type.value}\ndata: {event.model_dump_json(exclude_none=True)}\n\n"


@authenticated
@router.post("")
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    # Validate the model override up front so an unknown model is a clean 422, not an
    # error frame emitted after the SSE stream (and its 200) has already started.
    if request.model is not None:
        catalog.ensure_allowed(request.model)

    async def frames() -> AsyncIterator[str]:
        try:
            async for event in service.stream(
                request.message,
                request.context,
                model=request.model,
                effort=request.effort,
            ):
                yield _sse(event)
        except Exception as exc:  # noqa: BLE001 - headers are sent; report as an SSE error, not a 500
            logger.exception("chat stream failed")
            yield _sse(StreamEvent(type=StreamEventType.ERROR, error=str(exc)))
        yield _sse(StreamEvent(type=StreamEventType.DONE))

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
