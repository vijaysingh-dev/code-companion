import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.constants import StreamEventType
from app.models.message import Part, TextPart, ThinkingPart, ToolUsePart
from app.models.request import CompletionRequest
from app.models.response import CompletionResponse, StopReason, StreamEvent
from app.models.usage import Usage

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Raised when a provider returns a non-2xx response."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"provider returned {status_code}: {body[:500]}")


class BaseProvider(ABC):
    """Abstract async, streaming-first LLM provider.

    Concrete adapters implement four hooks — `_endpoint`, `_headers`,
    `_build_payload`, `_parse_sse` — that translate between the normalized types
    (`CompletionRequest` / `StreamEvent`) and a provider's wire format. Everything
    else (HTTP, SSE framing, accumulation into a `CompletionResponse`) is shared.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 600.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = (base_url or self.default_base_url).rstrip("/")
        # An injected client is owned by the caller; one we create, we close in aclose().
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

    # --- Hooks each provider must implement ------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical provider name (matches an LLMProvider value)."""

    @property
    @abstractmethod
    def default_base_url(self) -> str:
        """Base URL used when the caller doesn't override it."""

    @abstractmethod
    def _endpoint(self, request: CompletionRequest) -> str:
        """Absolute URL to POST for this request."""

    @abstractmethod
    def _headers(self) -> dict[str, str]:
        """Auth + content headers."""

    @abstractmethod
    def _build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        """Translate the normalized request into the provider's JSON body."""

    @abstractmethod
    def _parse_events(self, event_name: str | None, data: str, state: dict[str, Any]) -> list[StreamEvent]:
        """Translate one raw SSE record into zero or more normalized events.

        `state` is a fresh dict per `stream()` call (never shared across streams),
        so an adapter can carry partial info between records — e.g. Anthropic stashes
        input-token usage from `message_start` to combine with output tokens at
        `message_delta`. Return `[]` to skip a record (heartbeats, `[DONE]`).
        """

    # --- Public API ------------------------------------------------------------

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        """Yield normalized StreamEvents for the request."""
        payload = self._build_payload(request)
        url = self._endpoint(request)
        state: dict[str, Any] = {}
        async with self._client.stream("POST", url, headers=self._headers(), json=payload) as resp:
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", errors="replace")
                logger.error("%s stream error %s: %s", self.name, resp.status_code, body[:500])
                raise ProviderError(resp.status_code, body)
            async for event_name, data in self._read_sse(resp):
                for event in self._parse_events(event_name, data, state):
                    yield event

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Consume the stream and fold it into a single accumulated response."""
        model = request.model
        usage = Usage()
        stop_reason: StopReason | None = None
        builders: dict[int, dict[str, Any]] = {}
        order: list[int] = []

        def _builder(index: int) -> dict[str, Any]:
            if index not in builders:
                builders[index] = {}
                order.append(index)
            return builders[index]

        async for ev in self.stream(request):
            idx = ev.index if ev.index is not None else 0
            if ev.type == StreamEventType.MESSAGE_START:
                model = ev.model or model
            elif ev.type == StreamEventType.TEXT_DELTA:
                b = _builder(idx)
                b["kind"] = "text"
                b["text"] = b.get("text", "") + (ev.text or "")
            elif ev.type == StreamEventType.THINKING_DELTA:
                b = _builder(idx)
                b["kind"] = "thinking"
                b["text"] = b.get("text", "") + (ev.text or "")
            elif ev.type == StreamEventType.TOOL_USE_START:
                b = _builder(idx)
                b["kind"] = "tool"
                b["id"] = ev.tool_id or ""
                b["name"] = ev.tool_name or ""
                b.setdefault("args", "")
            elif ev.type == StreamEventType.TOOL_USE_DELTA:
                b = _builder(idx)
                b["kind"] = "tool"
                b["args"] = b.get("args", "") + (ev.tool_args_delta or "")
            elif ev.type == StreamEventType.USAGE and ev.usage is not None:
                usage = ev.usage  # providers report cumulative totals — take the latest
            elif ev.type == StreamEventType.STOP and ev.stop_reason is not None:
                stop_reason = ev.stop_reason

        content: list[Part] = [part for idx in order if (part := self._finalize(builders[idx])) is not None]
        return CompletionResponse(model=model, content=content, stop_reason=stop_reason, usage=usage)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # --- Shared helpers --------------------------------------------------------

    @staticmethod
    def _finalize(builder: dict[str, Any]) -> Part | None:
        kind = builder.get("kind")
        if kind == "text":
            return TextPart(text=builder.get("text", ""))
        if kind == "thinking":
            return ThinkingPart(text=builder.get("text", ""))
        if kind == "tool":
            raw = (builder.get("args") or "").strip()
            try:
                args = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                logger.warning("could not parse tool args as JSON: %r", raw[:200])
                args = {}
            return ToolUsePart(id=builder.get("id", ""), name=builder.get("name", ""), args=args)
        return None

    @staticmethod
    async def _read_sse(resp: httpx.Response) -> AsyncIterator[tuple[str | None, str]]:
        """Parse an SSE body into (event_name, data) records.

        Handles all three providers: Anthropic sends `event:`/`data:` pairs, OpenAI
        and Gemini send `data:`-only frames. Blank lines terminate a record; `:`
        lines are heartbeat comments.
        """
        event_name: str | None = None
        data_lines: list[str] = []
        async for raw in resp.aiter_lines():
            line = raw.rstrip("\r")
            if line == "":
                if data_lines:
                    yield event_name, "\n".join(data_lines)
                event_name = None
                data_lines = []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].lstrip(" "))
        if data_lines:
            yield event_name, "\n".join(data_lines)
