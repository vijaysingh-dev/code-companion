import json
import logging
from typing import Any

from app.core.constants import LLMProvider, StreamEventType
from app.llm.providers.base import BaseProvider
from app.models.message import (
    FilePart,
    ImagePart,
    Message,
    Role,
    TextPart,
    ThinkingPart,
    ToolResultPart,
    ToolUsePart,
)
from app.models.request import CompletionRequest
from app.models.response import StopReason, StreamEvent
from app.models.usage import Usage

logger = logging.getLogger(__name__)

# Anthropic stop_reason -> normalized StopReason.
_STOP_REASONS: dict[str, StopReason] = {
    "end_turn": StopReason.END_TURN,
    "max_tokens": StopReason.MAX_TOKENS,
    "tool_use": StopReason.TOOL_USE,
    "stop_sequence": StopReason.STOP_SEQUENCE,
    "refusal": StopReason.REFUSAL,
    "pause_turn": StopReason.END_TURN,
}

# Anthropic takes effort verbatim under `output_config.effort` (low|medium|high|max),
# but only on effort-capable models. Haiku rejects it, so it's skipped there.
_NO_EFFORT_MARKER = "haiku"


class AnthropicProvider(BaseProvider):
    """Adapter for the Anthropic Messages API (POST /v1/messages)."""

    @property
    def name(self) -> str:
        return LLMProvider.ANTHROPIC.value

    @property
    def default_base_url(self) -> str:
        return "https://api.anthropic.com"

    def _endpoint(self, request: CompletionRequest) -> str:
        return f"{self.base_url}/v1/messages"

    def _headers(self) -> dict[str, str]:
        return {
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    def _build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "stream": True,  # we always consume the streamed form
            "messages": [self._to_message(m) for m in request.messages if m.role is not Role.SYSTEM],
        }
        if request.system:
            payload["system"] = request.system
        if request.effort is not None and _NO_EFFORT_MARKER not in request.model:
            payload["output_config"] = {"effort": request.effort.value}
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop_sequences:
            payload["stop_sequences"] = request.stop_sequences
        if request.tools:
            payload["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.parameters} for t in request.tools
            ]
        if request.tool_choice is not None:
            payload["tool_choice"] = self._to_tool_choice(request)
        payload.update(request.extra)  # provider-specific escape hatch (e.g. "thinking")
        return payload

    # --- request translation ---------------------------------------------------

    @staticmethod
    def _to_tool_choice(request: CompletionRequest) -> dict[str, Any]:
        choice = request.tool_choice
        assert choice is not None
        if choice.name:
            return {"type": "tool", "name": choice.name}
        return {"type": choice.mode.value}  # auto | any | none

    def _to_message(self, message: Message) -> dict[str, Any]:
        # TOOL results are carried in a user turn on the Anthropic API.
        role = "assistant" if message.role is Role.ASSISTANT else "user"
        return {"role": role, "content": [self._to_block(p) for p in message.content]}

    @staticmethod
    def _to_block(part: Any) -> dict[str, Any]:
        if isinstance(part, TextPart):
            return {"type": "text", "text": part.text}
        if isinstance(part, ImagePart):
            source: dict[str, Any]
            if part.url:
                source = {"type": "url", "url": part.url}
            else:
                source = {"type": "base64", "media_type": part.mime_type, "data": part.data}
            return {"type": "image", "source": source}
        if isinstance(part, FilePart):
            if part.file_id:
                source = {"type": "file", "file_id": part.file_id}
            else:
                source = {"type": "base64", "media_type": part.mime_type, "data": part.data}
            return {"type": "document", "source": source}
        if isinstance(part, ToolUsePart):
            return {"type": "tool_use", "id": part.id, "name": part.name, "input": part.args}
        if isinstance(part, ToolResultPart):
            return {
                "type": "tool_result",
                "tool_use_id": part.tool_use_id,
                "content": part.content,
                "is_error": part.is_error,
            }
        if isinstance(part, ThinkingPart):
            return {"type": "text", "text": part.text}  # not replayed as thinking on input
        raise ValueError(f"unsupported content part: {type(part).__name__}")

    # --- response translation --------------------------------------------------

    def _parse_events(self, event_name: str | None, data: str, state: dict[str, Any]) -> list[StreamEvent]:
        if data in ("", "[DONE]"):
            return []
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            logger.warning("anthropic: undecodable SSE data: %r", data[:200])
            return []

        if event_name == "message_start":
            msg = obj.get("message", {})
            usage = msg.get("usage", {})
            state["usage"] = Usage(
                input_tokens=usage.get("input_tokens", 0),
                cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                cache_write_tokens=usage.get("cache_creation_input_tokens", 0),
            )
            return [StreamEvent(type=StreamEventType.MESSAGE_START, model=msg.get("model"))]

        if event_name == "content_block_start":
            index = obj.get("index", 0)
            block = obj.get("content_block", {})
            if block.get("type") == "tool_use":
                state.setdefault("tool_indices", set()).add(index)
                return [
                    StreamEvent(
                        type=StreamEventType.TOOL_USE_START,
                        index=index,
                        tool_id=block.get("id"),
                        tool_name=block.get("name"),
                    )
                ]
            return []

        if event_name == "content_block_delta":
            index = obj.get("index", 0)
            delta = obj.get("delta", {})
            dtype = delta.get("type")
            if dtype == "text_delta":
                return [StreamEvent(type=StreamEventType.TEXT_DELTA, index=index, text=delta.get("text", ""))]
            if dtype == "thinking_delta":
                return [StreamEvent(type=StreamEventType.THINKING_DELTA, index=index, text=delta.get("thinking", ""))]
            if dtype == "input_json_delta":
                return [
                    StreamEvent(
                        type=StreamEventType.TOOL_USE_DELTA,
                        index=index,
                        tool_args_delta=delta.get("partial_json", ""),
                    )
                ]
            return []

        if event_name == "content_block_stop":
            index = obj.get("index", 0)
            if index in state.get("tool_indices", set()):
                return [StreamEvent(type=StreamEventType.TOOL_USE_STOP, index=index)]
            return []

        if event_name == "message_delta":
            events: list[StreamEvent] = []
            usage = state.get("usage", Usage()).model_copy()
            out = obj.get("usage", {})
            usage.output_tokens = out.get("output_tokens", usage.output_tokens)
            events.append(StreamEvent(type=StreamEventType.USAGE, usage=usage))
            reason = obj.get("delta", {}).get("stop_reason")
            if reason:
                events.append(
                    StreamEvent(type=StreamEventType.STOP, stop_reason=_STOP_REASONS.get(reason, StopReason.END_TURN))
                )
            return events

        if event_name == "error":
            return [StreamEvent(type=StreamEventType.ERROR, error=obj.get("error", {}).get("message", "unknown error"))]

        return []  # message_stop, ping, etc.
