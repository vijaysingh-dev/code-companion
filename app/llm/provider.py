import logging
from typing import Literal

import httpx

from app.core.config import settings
from app.core.constants import LLMProvider
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.base import BaseProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)

# Identifier -> adapter class. `llama` reuses the OpenAI adapter (OpenAI-compatible
# wire format) with a caller-supplied base URL; `google` maps to Gemini.
_ADAPTERS: dict[LLMProvider, type[BaseProvider]] = {
    LLMProvider.OPENAI: OpenAIProvider,
    LLMProvider.LLAMA: OpenAIProvider,
    LLMProvider.ANTHROPIC: AnthropicProvider,
    LLMProvider.GOOGLE: GeminiProvider,
}


def build_provider(
    provider: LLMProvider | str,
    api_key: str,
    base_url: str | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> BaseProvider:
    """Construct an adapter for an explicit provider/credentials pair."""
    try:
        adapter = _ADAPTERS[LLMProvider(provider)]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported LLM provider: {provider!r}") from exc
    return adapter(api_key=api_key, base_url=base_url or None, client=client)


def get_provider(
    tier: Literal["main", "mini"] = "main",
    *,
    client: httpx.AsyncClient | None = None,
) -> BaseProvider:
    """Build the adapter for a configured tier (from `settings`).

    `main` is the reasoning/coding model; `mini` is the cheap/fast tier. The mini
    tier's provider/credentials are resolved in `Settings` (inherited from main when
    on the same provider). The model id itself lives in settings.{LLM,MINI_LLM}_MODEL
    and is set on each CompletionRequest by the caller — the adapter is model-agnostic.
    """
    if tier == "mini":
        return build_provider(
            settings.MINI_LLM_PROVIDER or settings.LLM_PROVIDER,
            settings.MINI_LLM_API_KEY or "",
            settings.MINI_LLM_BASE_URL or None,
            client=client,
        )
    return build_provider(
        settings.LLM_PROVIDER,
        settings.LLM_API_KEY,
        settings.LLM_BASE_URL or None,
        client=client,
    )
