from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Tool(BaseModel):
    """A callable tool exposed to the model.

    `parameters` is a JSON Schema object. Each adapter wraps it in the provider's
    envelope: Anthropic `input_schema`, OpenAI `function.parameters`, Gemini
    `functionDeclarations[].parameters`.
    """

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})


class ToolChoiceMode(str, Enum):
    AUTO = "auto"  # model decides (default)
    ANY = "any"  # must call some tool (OpenAI "required", Gemini "ANY")
    NONE = "none"  # never call a tool


class ToolChoice(BaseModel):
    """How the model is allowed to use tools.

    Set `name` to force one specific tool (implies a single required call). Leave
    it unset and pick a `mode` for the general cases.
    """

    mode: ToolChoiceMode = ToolChoiceMode.AUTO
    name: str | None = None  # force this specific tool when set
