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
from app.models.tool import ToolChoiceMode
from app.models.usage import Usage

logger = logging.getLogger(__name__)

# Gemini finishReason -> normalized StopReason.
_STOP_REASONS: dict[str, StopReason] = {
    "STOP": StopReason.END_TURN,
    "MAX_TOKENS": StopReason.MAX_TOKENS,
    "SAFETY": StopReason.REFUSAL,
    "RECITATION": StopReason.REFUSAL,
    "PROHIBITED_CONTENT": StopReason.REFUSAL,
    "OTHER": StopReason.END_TURN,
}

_TOOL_CHOICE_MODES: dict[ToolChoiceMode, str] = {
    ToolChoiceMode.AUTO: "AUTO",
    ToolChoiceMode.ANY: "ANY",
    ToolChoiceMode.NONE: "NONE",
}

_TOOL_INDEX_OFFSET = 100


class GeminiProvider(BaseProvider):
    """Adapter for the Google Gemini generateContent API (streamGenerateContent)."""

    @property
    def name(self) -> str:
        return LLMProvider.GOOGLE.value

    @property
    def default_base_url(self) -> str:
        return "https://generativelanguage.googleapis.com"

    def _endpoint(self, request: CompletionRequest) -> str:
        return f"{self.base_url}/v1beta/models/{request.model}:streamGenerateContent?alt=sse"

    def _headers(self) -> dict[str, str]:
        return {"content-type": "application/json", "x-goog-api-key": self.api_key}

    def _build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "contents": [self._to_content(m) for m in request.messages if m.role is not Role.SYSTEM],
        }
        if request.system:
            payload["systemInstruction"] = {"parts": [{"text": request.system}]}

        # request.effort is not translated yet — Gemini expresses it via thinkingConfig
        # (a token budget), whose mapping is deferred; callers can set it through extra.
        generation_config: dict[str, Any] = {"maxOutputTokens": request.max_tokens}
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.top_p is not None:
            generation_config["topP"] = request.top_p
        if request.stop_sequences:
            generation_config["stopSequences"] = request.stop_sequences
        payload["generationConfig"] = generation_config

        if request.tools:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        {"name": t.name, "description": t.description, "parameters": t.parameters}
                        for t in request.tools
                    ]
                }
            ]
        if request.tool_choice is not None:
            payload["toolConfig"] = self._to_tool_config(request)
        payload.update(request.extra)  # provider-specific escape hatch (e.g. "safetySettings")
        return payload

    # --- request translation ---------------------------------------------------

    @staticmethod
    def _to_tool_config(request: CompletionRequest) -> dict[str, Any]:
        choice = request.tool_choice
        assert choice is not None
        if choice.name:
            return {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": [choice.name]}}
        return {"functionCallingConfig": {"mode": _TOOL_CHOICE_MODES[choice.mode]}}

    def _to_content(self, message: Message) -> dict[str, Any]:
        # Gemini uses "model" for the assistant; tool results ride in a user turn.
        role = "model" if message.role is Role.ASSISTANT else "user"
        return {"role": role, "parts": [self._to_part(p) for p in message.content]}

    @staticmethod
    def _to_part(part: Any) -> dict[str, Any]:
        if isinstance(part, TextPart):
            return {"text": part.text}
        if isinstance(part, ThinkingPart):
            return {"text": part.text}
        if isinstance(part, ImagePart):
            if part.data:
                return {"inlineData": {"mimeType": part.mime_type, "data": part.data}}
            return {"fileData": {"mimeType": part.mime_type, "fileUri": part.url}}
        if isinstance(part, FilePart):
            if part.data:
                return {"inlineData": {"mimeType": part.mime_type, "data": part.data}}
            return {"fileData": {"mimeType": part.mime_type, "fileUri": part.uri or part.file_id}}
        if isinstance(part, ToolUsePart):
            return {"functionCall": {"name": part.name, "args": part.args}}
        if isinstance(part, ToolResultPart):
            # Gemini correlates by name (no call id); tool_use_id carries the name.
            response = {"error": part.content} if part.is_error else {"result": part.content}
            return {"functionResponse": {"name": part.tool_use_id, "response": response}}
        raise ValueError(f"unsupported content part: {type(part).__name__}")

    # --- response translation --------------------------------------------------

    def _parse_events(self, event_name: str | None, data: str, state: dict[str, Any]) -> list[StreamEvent]:
        if data in ("", "[DONE]"):
            return []
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            logger.warning("gemini: undecodable SSE data: %r", data[:200])
            return []

        events: list[StreamEvent] = []
        if not state.get("started"):
            state["started"] = True
            events.append(StreamEvent(type=StreamEventType.MESSAGE_START, model=obj.get("modelVersion")))

        for candidate in obj.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                events.extend(self._part_events(part, state))
            reason = candidate.get("finishReason")
            if reason:
                stop = StopReason.TOOL_USE if state.get("saw_tool") else _STOP_REASONS.get(reason, StopReason.END_TURN)
                events.append(StreamEvent(type=StreamEventType.STOP, stop_reason=stop))

        meta = obj.get("usageMetadata")
        if meta:
            events.append(StreamEvent(type=StreamEventType.USAGE, usage=self._to_usage(meta)))
        return events

    @staticmethod
    def _part_events(part: dict[str, Any], state: dict[str, Any]) -> list[StreamEvent]:
        if "functionCall" in part:
            fc = part["functionCall"]
            state["saw_tool"] = True
            index = _TOOL_INDEX_OFFSET + state.get("tool_count", 0)
            state["tool_count"] = state.get("tool_count", 0) + 1
            name = fc.get("name", "")
            return [
                # Gemini returns whole args at once; id carries the name (no call id).
                StreamEvent(type=StreamEventType.TOOL_USE_START, index=index, tool_id=name, tool_name=name),
                StreamEvent(
                    type=StreamEventType.TOOL_USE_DELTA, index=index, tool_args_delta=json.dumps(fc.get("args", {}))
                ),
                StreamEvent(type=StreamEventType.TOOL_USE_STOP, index=index),
            ]
        if "text" in part:
            kind = StreamEventType.THINKING_DELTA if part.get("thought") else StreamEventType.TEXT_DELTA
            return [StreamEvent(type=kind, index=0, text=part["text"])]
        return []

    @staticmethod
    def _to_usage(meta: dict[str, Any]) -> Usage:
        return Usage(
            input_tokens=meta.get("promptTokenCount", 0),
            output_tokens=meta.get("candidatesTokenCount", 0),
            cache_read_tokens=meta.get("cachedContentTokenCount", 0),
            thinking_tokens=meta.get("thoughtsTokenCount", 0),
        )
