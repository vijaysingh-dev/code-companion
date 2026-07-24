import json
import logging
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import quote

import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from botocore.eventstream import EventStreamBuffer

from app.core.constants import LLMProvider, StreamEventType
from app.llm.providers.base import BaseProvider, ProviderError
from app.models.message import Message, Role, TextPart, ThinkingPart, ToolResultPart, ToolUsePart
from app.models.request import CompletionRequest
from app.models.response import StopReason, StreamEvent
from app.models.usage import Usage

logger = logging.getLogger(__name__)

_SERVICE = "bedrock"

# Converse stopReason -> normalized StopReason.
_STOP_REASONS: dict[str, StopReason] = {
    "end_turn": StopReason.END_TURN,
    "tool_use": StopReason.TOOL_USE,
    "max_tokens": StopReason.MAX_TOKENS,
    "stop_sequence": StopReason.STOP_SEQUENCE,
    "content_filtered": StopReason.REFUSAL,
    "guardrail_intervened": StopReason.REFUSAL,
}


class BedrockConverseProvider(BaseProvider):
    """AWS Bedrock via the unified Converse API (POST /model/{id}/converse-stream).

    Auth is SigV4 (region + AWS credentials), and the response is AWS event-stream
    binary framing, not SSE — so `stream()` is overridden to sign the request and
    decode frames with botocore, while the shared HTTP client still does the I/O.
    """

    def __init__(
        self,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        *,
        session_token: str | None = None,
        client: httpx.AsyncClient | None = None,
        timeout: float = 600.0,
    ) -> None:
        self._region = region
        self._creds = Credentials(access_key_id, secret_access_key, session_token)
        super().__init__(api_key="", base_url=self.default_base_url, client=client, timeout=timeout)

    @property
    def name(self) -> str:
        return LLMProvider.BEDROCK.value

    @property
    def default_base_url(self) -> str:
        return f"https://bedrock-runtime.{self._region}.amazonaws.com"

    def _endpoint(self, request: CompletionRequest) -> str:
        # The model id (e.g. anthropic....:0) must be percent-encoded so the sent path
        # matches SigV4's canonical path exactly.
        return f"{self.base_url}/model/{quote(request.model, safe='')}/converse-stream"

    def _headers(self) -> dict[str, str]:
        return {"content-type": "application/json"}

    def _build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        inference: dict[str, Any] = {"maxTokens": request.max_tokens}
        if request.temperature is not None:
            inference["temperature"] = request.temperature
        if request.top_p is not None:
            inference["topP"] = request.top_p
        if request.stop_sequences:
            inference["stopSequences"] = request.stop_sequences

        payload: dict[str, Any] = {
            "messages": [self._to_message(m) for m in request.messages if m.role is not Role.SYSTEM],
            "inferenceConfig": inference,
        }
        if request.system:
            payload["system"] = [{"text": request.system}]
        if request.tools:
            tool_config: dict[str, Any] = {
                "tools": [
                    {"toolSpec": {"name": t.name, "description": t.description, "inputSchema": {"json": t.parameters}}}
                    for t in request.tools
                ]
            }
            choice = self._to_tool_choice(request)
            if choice is not None:
                tool_config["toolChoice"] = choice
            payload["toolConfig"] = tool_config
        # TODO: map effort to additionalModelRequestFields (model-family specific).
        payload.update(request.extra)
        return payload

    @staticmethod
    def _to_tool_choice(request: CompletionRequest) -> dict[str, Any] | None:
        choice = request.tool_choice
        if choice is None:
            return None
        if choice.name:
            return {"tool": {"name": choice.name}}
        # Converse supports auto/any only; NONE has no equivalent, so omit the choice.
        return {choice.mode.value: {}} if choice.mode.value in ("auto", "any") else None

    def _to_message(self, message: Message) -> dict[str, Any]:
        role = "assistant" if message.role is Role.ASSISTANT else "user"
        return {"role": role, "content": [self._to_block(p) for p in message.content]}

    @staticmethod
    def _to_block(part: Any) -> dict[str, Any]:
        if isinstance(part, (TextPart, ThinkingPart)):
            return {"text": part.text}
        if isinstance(part, ToolUsePart):
            return {"toolUse": {"toolUseId": part.id, "name": part.name, "input": part.args}}
        if isinstance(part, ToolResultPart):
            return {
                "toolResult": {
                    "toolUseId": part.tool_use_id,
                    "content": [{"text": part.content}],
                    "status": "error" if part.is_error else "success",
                }
            }
        # TODO: image/document content blocks for Bedrock Converse.
        raise ValueError(f"unsupported content part for Bedrock: {type(part).__name__}")

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        url = self._endpoint(request)
        body = json.dumps(self._build_payload(request)).encode("utf-8")
        signed = AWSRequest(method="POST", url=url, data=body, headers=self._headers())
        SigV4Auth(self._creds, _SERVICE, self._region).add_auth(signed)

        state: dict[str, Any] = {}
        buffer = EventStreamBuffer()
        async with self._client.stream("POST", url, headers=dict(signed.headers), content=body) as resp:
            if resp.status_code >= 400:
                text = (await resp.aread()).decode("utf-8", errors="replace")
                logger.error("bedrock stream error %s: %s", resp.status_code, text[:500])
                raise ProviderError(resp.status_code, text)
            async for chunk in resp.aiter_bytes():
                buffer.add_data(chunk)
                for message in buffer:
                    for event in self._translate(message, state):
                        yield event

    def _translate(self, message: Any, state: dict[str, Any]) -> list[StreamEvent]:
        headers = message.headers
        if headers.get(":message-type") in ("exception", "error"):
            kind = headers.get(":exception-type") or headers.get(":error-code") or "error"
            return [
                StreamEvent(type=StreamEventType.ERROR, error=f"{kind}: {message.payload.decode('utf-8', 'replace')}")
            ]
        data = message.payload.decode("utf-8") if message.payload else ""
        return self._parse_events(headers.get(":event-type"), data, state)

    def _parse_events(self, event_name: str | None, data: str, state: dict[str, Any]) -> list[StreamEvent]:
        try:
            obj = json.loads(data) if data else {}
        except json.JSONDecodeError:
            logger.warning("bedrock: undecodable payload: %r", data[:200])
            return []

        if event_name == "messageStart":
            return [StreamEvent(type=StreamEventType.MESSAGE_START)]
        if event_name == "contentBlockStart":
            index = obj.get("contentBlockIndex", 0)
            tool = obj.get("start", {}).get("toolUse")
            if tool:
                state.setdefault("tool_indices", set()).add(index)
                return [
                    StreamEvent(
                        type=StreamEventType.TOOL_USE_START,
                        index=index,
                        tool_id=tool.get("toolUseId"),
                        tool_name=tool.get("name"),
                    )
                ]
            return []
        if event_name == "contentBlockDelta":
            return self._delta_events(obj)
        if event_name == "contentBlockStop":
            index = obj.get("contentBlockIndex", 0)
            if index in state.get("tool_indices", set()):
                return [StreamEvent(type=StreamEventType.TOOL_USE_STOP, index=index)]
            return []
        if event_name == "messageStop":
            reason = str(obj.get("stopReason") or "")
            return [StreamEvent(type=StreamEventType.STOP, stop_reason=_STOP_REASONS.get(reason, StopReason.END_TURN))]
        if event_name == "metadata":
            usage = obj.get("usage", {})
            return [
                StreamEvent(
                    type=StreamEventType.USAGE,
                    usage=Usage(input_tokens=usage.get("inputTokens", 0), output_tokens=usage.get("outputTokens", 0)),
                )
            ]
        return []

    @staticmethod
    def _delta_events(obj: dict[str, Any]) -> list[StreamEvent]:
        index = obj.get("contentBlockIndex", 0)
        delta = obj.get("delta", {})
        if "text" in delta:
            return [StreamEvent(type=StreamEventType.TEXT_DELTA, index=index, text=delta["text"])]
        if "toolUse" in delta:
            return [
                StreamEvent(
                    type=StreamEventType.TOOL_USE_DELTA, index=index, tool_args_delta=delta["toolUse"].get("input", "")
                )
            ]
        reasoning = delta.get("reasoningContent", {})
        if "text" in reasoning:
            return [StreamEvent(type=StreamEventType.THINKING_DELTA, index=index, text=reasoning["text"])]
        return []
