from typing import Any

from pydantic import BaseModel, Field

from app.core.constants import Effort
from app.models.message import Message
from app.models.tool import Tool, ToolChoice


class CompletionRequest(BaseModel):
    """Provider-agnostic completion request.

    The typed fields cover what every provider supports; anything provider-specific
    (Anthropic `thinking`, OpenAI `reasoning_effort`, Gemini `safetySettings` /
    `thinkingConfig`, etc.) goes in `extra`, which each adapter shallow-merges into
    its wire payload. This keeps the shared interface small without blocking access
    to per-provider knobs.
    """

    model: str
    messages: list[Message]
    system: str | None = None

    max_tokens: int = 1024
    # effort => the main tier's control (translated per provider); temperature => the mini
    # tier's. None on either means "don't send it".
    effort: Effort | None = None
    temperature: float | None = None
    top_p: float | None = None
    stop_sequences: list[str] = Field(default_factory=list)

    tools: list[Tool] = Field(default_factory=list)
    tool_choice: ToolChoice | None = None

    stream: bool = True

    # Raw provider-specific fields, merged into the outgoing payload by the adapter.
    extra: dict[str, Any] = Field(default_factory=dict)
