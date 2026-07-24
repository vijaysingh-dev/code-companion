import logging

import httpx

from app.core.constants import LLMProvider
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.azure import AzureOpenAIProvider
from app.llm.providers.base import BaseProvider
from app.llm.providers.bedrock import BedrockConverseProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)

# `llama` reuses the OpenAI adapter (OpenAI-compatible wire) with a caller-supplied base URL.
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
    api_version: str | None = None,
    region: str | None = None,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    aws_session_token: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> BaseProvider:
    """Construct an adapter for an explicit provider/credentials pair."""
    try:
        resolved = LLMProvider(provider)
    except ValueError as exc:
        raise ValueError(f"unsupported LLM provider: {provider!r}") from exc

    if resolved is LLMProvider.AZURE:
        return AzureOpenAIProvider(api_key, base_url or "", api_version=api_version or "", client=client)
    if resolved is LLMProvider.BEDROCK:
        return BedrockConverseProvider(
            region or "",
            aws_access_key_id or "",
            aws_secret_access_key or "",
            session_token=aws_session_token,
            client=client,
        )

    return _ADAPTERS[resolved](api_key=api_key, base_url=base_url or None, client=client)
