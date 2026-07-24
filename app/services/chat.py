import logging
from collections.abc import AsyncIterator

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import Effort, StreamEventType
from app.llm.prompt import prompts
from app.llm.provider import build_provider
from app.models.message import Message
from app.models.request import CompletionRequest
from app.models.response import StreamEvent
from app.models.usage import Usage
from app.services import catalog
from app.services.catalog import ResolvedModel
from app.services.session import SessionService

logger = logging.getLogger(__name__)

# Rough char budget for replayed history before dropping oldest turns.
# TODO: token-based budget + mini-tier summarization instead of a flat char cap.
_MAX_HISTORY_CHARS = 24000


def _compact(messages: list[Message]) -> list[Message]:
    """Keep the most recent turns whose text fits the budget (oldest dropped first)."""
    total = 0
    kept: list[Message] = []
    for message in reversed(messages):
        total += len(message.text)
        if total > _MAX_HISTORY_CHARS and kept:
            break
        kept.append(message)
    return list(reversed(kept))


class ChatService:
    """Runs a chat turn against a persisted session: load history -> stream -> persist.

    Conversation history lives server-side (roadmap Slice D). The provider is built per
    turn from the session's resolved model over the shared HTTP client.
    """

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession], client: httpx.AsyncClient) -> None:
        self._sessionmaker = sessionmaker
        self._client = client

    async def prepare_turn(
        self,
        user_id: str,
        session_id: str,
        message: str,
        provider: str | None,
        model: str | None,
    ) -> tuple[ResolvedModel, list[Message]]:
        """Validate ownership + selection, persist the user turn, return the replay messages.

        Runs before streaming so a bad session (404) or model (422) is a clean HTTP error
        rather than an SSE frame after the stream has started.
        """
        async with self._sessionmaker() as db:
            service = SessionService(db)
            session = await service.get(user_id, session_id)
            resolved = catalog.resolve(provider or session.provider, model or session.model)
            history = await service.history(session_id)
            user_message = Message.user(message)
            await service.add_message(session_id, user_message)
            await service.touch(session_id, resolved.provider.value, resolved.model)
        return resolved, _compact(history) + [user_message]

    async def stream_turn(
        self,
        session_id: str,
        resolved: ResolvedModel,
        messages: list[Message],
        context: str | None,
        effort: Effort | None,
    ) -> AsyncIterator[StreamEvent]:
        logger.info(
            "Streaming turn (session=%s, provider=%s, model=%s)", session_id, resolved.provider.value, resolved.model
        )
        provider = build_provider(
            resolved.provider,
            resolved.api_key,
            resolved.base_url,
            api_version=resolved.api_version,
            region=resolved.region,
            aws_access_key_id=resolved.aws_access_key_id,
            aws_secret_access_key=resolved.aws_secret_access_key,
            aws_session_token=resolved.aws_session_token,
            client=self._client,
        )
        request = CompletionRequest(
            model=resolved.model,
            system=prompts.render("system", context=context or ""),
            messages=messages,
            max_tokens=resolved.max_tokens,
            effort=effort,
        )

        text_parts: list[str] = []
        usage: Usage | None = None
        async for event in provider.stream(request):
            if event.type is StreamEventType.TEXT_DELTA and event.text:
                text_parts.append(event.text)
            elif event.type is StreamEventType.USAGE:
                usage = event.usage
            yield event

        text = "".join(text_parts)
        if text:
            async with self._sessionmaker() as db:
                await SessionService(db).add_message(session_id, Message.assistant(text), usage=usage)
