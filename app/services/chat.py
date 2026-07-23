import logging
from collections.abc import AsyncIterator

from app.core.config import settings
from app.core.constants import Effort
from app.llm.prompt import prompts
from app.llm.providers.base import BaseProvider
from app.models.message import Message
from app.models.request import CompletionRequest
from app.models.response import StreamEvent

logger = logging.getLogger(__name__)


class ChatService:
    """Turns a user message into a streamed LLM response (roadmap S0.2).

    Assembles the normalized `CompletionRequest` — system prompt from the
    `PromptManager`, the user turn, and generation params from `settings` — and
    streams normalized `StreamEvent`s from the provider. Tool use and retrieved
    context feed in here later (the agent loop / Phase 4).
    """

    def __init__(self, provider: BaseProvider) -> None:
        self._provider = provider

    async def stream(
        self,
        message: str,
        context: str | None = None,
        *,
        model: str | None = None,
        effort: Effort | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a reply. `model`/`effort` are client overrides; None => server default.

        A non-None `model` is assumed already validated against the catalog (the router
        does that before streaming, so a bad value fails as a clean 4xx, not mid-stream).
        """
        model = model or settings.LLM_MODEL
        logger.info("Streaming chat (model=%s, effort=%s, has_context=%s)", model, effort, context is not None)
        request = CompletionRequest(
            model=model,
            system=prompts.render("system", context=context or ""),
            messages=[Message.user(message)],
            max_tokens=settings.LLM_MAX_TOKENS,
            effort=effort,
        )
        async for event in self._provider.stream(request):
            yield event
