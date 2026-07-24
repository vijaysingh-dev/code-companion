import logging

import httpx

from app.core.constants import LLMProvider
from app.llm.providers.openai import OpenAIProvider
from app.models.request import CompletionRequest

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(OpenAIProvider):
    """Azure OpenAI — the OpenAI wire format with Azure's URL shape and auth.

    `base_url` is the resource endpoint (https://<name>.openai.azure.com) and the
    model id is the *deployment* name, placed in the path with `api-version` as a
    query param. Auth is the `api-key` header, not a bearer token.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        api_version: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 600.0,
    ) -> None:
        super().__init__(api_key, base_url, client=client, timeout=timeout)
        self._api_version = api_version

    @property
    def name(self) -> str:
        return LLMProvider.AZURE.value

    @property
    def default_base_url(self) -> str:
        return ""

    def _endpoint(self, request: CompletionRequest) -> str:
        return f"{self.base_url}/openai/deployments/{request.model}/chat/completions?api-version={self._api_version}"

    def _headers(self) -> dict[str, str]:
        return {"content-type": "application/json", "api-key": self.api_key}
