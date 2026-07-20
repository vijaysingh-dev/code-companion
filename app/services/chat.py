import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Answers a user message. Currently a hardcoded stub (roadmap S0.1).

    Next steps: swap the stub for an `LLMProvider` call with token streaming
    (S0.2), then feed retrieved chunks in as `context` (Phase 4).
    """

    async def answer(self, message: str, context: str | None = None) -> str:
        logger.info("Answering message (len=%d, has_context=%s)", len(message), context is not None)
        # TODO(S0.2): call the LLM provider instead of echoing.
        return f"You said: {message}"
