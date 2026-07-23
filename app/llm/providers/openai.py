import json
import logging
from typing import Any

from app.core.constants import Effort, LLMProvider, StreamEventType
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
from app.models.tool import ToolChoiceMode
from app.models.usage import Usage

logger = logging.getLogger(__name__)

# OpenAI finish_reason -> normalized StopReason.
_STOP_REASONS: dict[str, StopReason] = {
    "stop": StopReason.END_TURN,
    "length": StopReason.MAX_TOKENS,
    "tool_calls": StopReason.TOOL_USE,
    "function_call": StopReason.TOOL_USE,
    "content_filter": StopReason.REFUSAL,
}

# Tool blocks get their own index space so they never collide with text (index 0).
_TOOL_INDEX_OFFSET = 100

# Effort applies only to reasoning models via `reasoning_effort`; OpenAI has no "max",
# so it collapses onto "high". Non-reasoning models (gpt-4o, llama) reject the field,
# so effort is omitted for them (see _is_reasoning_model).
_REASONING_EFFORT: dict[Effort, str] = {
    Effort.LOW: "low",
    Effort.MEDIUM: "medium",
    Effort.HIGH: "high",
    Effort.MAX: "high",
}
_REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")


class OpenAIProvider(BaseProvider):
    """Adapter for the OpenAI Chat Completions API (POST /v1/chat/completions).

    Also serves any OpenAI-compatible endpoint (the `llama` identifier, Groq,
    Together, Ollama, …) — the factory constructs it with the appropriate base URL.
    """

    @property
    def name(self) -> str:
        return LLMProvider.OPENAI.value

    @property
    def default_base_url(self) -> str:
        return "https://api.openai.com"

    def _endpoint(self, request: CompletionRequest) -> str:
        return f"{self.base_url}/v1/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {"content-type": "application/json", "authorization": f"Bearer {self.api_key}"}

    def _build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        for message in request.messages:
            messages.extend(self._to_messages(message))

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_completion_tokens": request.max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if request.effort is not None and self._is_reasoning_model(request.model):
            payload["reasoning_effort"] = _REASONING_EFFORT[request.effort]
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop_sequences:
            payload["stop"] = request.stop_sequences
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
                }
                for t in request.tools
            ]
        if request.tool_choice is not None:
            payload["tool_choice"] = self._to_tool_choice(request)
        payload.update(request.extra)  # provider-specific escape hatch (e.g. "reasoning_effort")
        return payload

    # --- request translation ---------------------------------------------------

    @staticmethod
    def _is_reasoning_model(model: str) -> bool:
        return model.startswith(_REASONING_PREFIXES)

    @staticmethod
    def _to_tool_choice(request: CompletionRequest) -> Any:
        choice = request.tool_choice
        assert choice is not None
        if choice.name:
            return {"type": "function", "function": {"name": choice.name}}
        return {ToolChoiceMode.AUTO: "auto", ToolChoiceMode.ANY: "required", ToolChoiceMode.NONE: "none"}[choice.mode]

    def _to_messages(self, message: Message) -> list[dict[str, Any]]:
        tool_results = [p for p in message.content if isinstance(p, ToolResultPart)]
        if tool_results:
            # Each tool result becomes its own `role: "tool"` message.
            return [{"role": "tool", "tool_call_id": p.tool_use_id, "content": p.content} for p in tool_results]

        if message.role is Role.ASSISTANT:
            out: dict[str, Any] = {"role": "assistant"}
            text = "".join(p.text for p in message.content if isinstance(p, (TextPart, ThinkingPart)))
            tool_calls = [
                {
                    "id": p.id,
                    "type": "function",
                    "function": {"name": p.name, "arguments": json.dumps(p.args)},
                }
                for p in message.content
                if isinstance(p, ToolUsePart)
            ]
            out["content"] = text or None
            if tool_calls:
                out["tool_calls"] = tool_calls
            return [out]

        role = "system" if message.role is Role.SYSTEM else "user"
        return [{"role": role, "content": self._to_content(message)}]

    @staticmethod
    def _to_content(message: Message) -> Any:
        parts: list[dict[str, Any]] = []
        for part in message.content:
            if isinstance(part, TextPart):
                parts.append({"type": "text", "text": part.text})
            elif isinstance(part, ImagePart):
                url = part.url or f"data:{part.mime_type};base64,{part.data}"
                parts.append({"type": "image_url", "image_url": {"url": url}})
            elif isinstance(part, FilePart):
                if part.file_id:
                    parts.append({"type": "file", "file": {"file_id": part.file_id}})
                else:
                    parts.append({"type": "file", "file": {"file_data": f"data:{part.mime_type};base64,{part.data}"}})
        # A lone text part can be sent as a plain string.
        if len(parts) == 1 and parts[0]["type"] == "text":
            return parts[0]["text"]
        return parts

    # --- response translation --------------------------------------------------

    def _parse_events(self, event_name: str | None, data: str, state: dict[str, Any]) -> list[StreamEvent]:
        if data in ("", "[DONE]"):
            return []
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            logger.warning("openai: undecodable SSE data: %r", data[:200])
            return []

        events: list[StreamEvent] = []
        if not state.get("started"):
            state["started"] = True
            events.append(StreamEvent(type=StreamEventType.MESSAGE_START, model=obj.get("model")))

        for choice in obj.get("choices", []):
            delta = choice.get("delta", {})
            if delta.get("content"):
                events.append(StreamEvent(type=StreamEventType.TEXT_DELTA, index=0, text=delta["content"]))
            for tc in delta.get("tool_calls", []):
                events.extend(self._tool_call_events(tc, state))
            reason = choice.get("finish_reason")
            if reason:
                events.append(
                    StreamEvent(type=StreamEventType.STOP, stop_reason=_STOP_REASONS.get(reason, StopReason.END_TURN))
                )

        usage = obj.get("usage")
        if usage:
            events.append(StreamEvent(type=StreamEventType.USAGE, usage=self._to_usage(usage)))
        return events

    @staticmethod
    def _tool_call_events(tc: dict[str, Any], state: dict[str, Any]) -> list[StreamEvent]:
        index = _TOOL_INDEX_OFFSET + tc.get("index", 0)
        fn = tc.get("function", {})
        events: list[StreamEvent] = []
        seen: set[int] = state.setdefault("tool_seen", set())
        if index not in seen:
            seen.add(index)
            events.append(
                StreamEvent(
                    type=StreamEventType.TOOL_USE_START, index=index, tool_id=tc.get("id"), tool_name=fn.get("name")
                )
            )
        if fn.get("arguments"):
            events.append(
                StreamEvent(type=StreamEventType.TOOL_USE_DELTA, index=index, tool_args_delta=fn["arguments"])
            )
        return events

    @staticmethod
    def _to_usage(usage: dict[str, Any]) -> Usage:
        prompt_details = usage.get("prompt_tokens_details") or {}
        completion_details = usage.get("completion_tokens_details") or {}
        return Usage(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            cache_read_tokens=prompt_details.get("cached_tokens", 0),
            thinking_tokens=completion_details.get("reasoning_tokens", 0),
        )
