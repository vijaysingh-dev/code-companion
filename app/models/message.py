from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Conversation roles in the normalized model.

    `SYSTEM` is only used for standalone system content; in a request the system
    prompt is carried on `CompletionRequest.system`, and adapters place it where
    each provider expects it (top-level for Anthropic/Gemini, a message for OpenAI).
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ImagePart(BaseModel):
    type: Literal["image"] = "image"
    mime_type: str
    data: str | None = None  # base64, no newlines
    url: str | None = None  # remote URL (mutually exclusive with data)


class FilePart(BaseModel):
    type: Literal["file"] = "file"
    mime_type: str
    file_id: str | None = None  # provider Files-API id
    data: str | None = None  # inline base64
    uri: str | None = None  # provider file URI (Gemini fileData)


class ToolUsePart(BaseModel):
    """An assistant's request to call a tool (Anthropic tool_use / OpenAI
    tool_calls / Gemini functionCall). Args are always a parsed object here."""

    type: Literal["tool_use"] = "tool_use"
    id: str  # correlation id; empty for Gemini (correlate by name)
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResultPart(BaseModel):
    """The result of a tool call, fed back on the next turn."""

    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str  # matches the ToolUsePart.id (or the tool name for Gemini)
    content: str
    is_error: bool = False


class ThinkingPart(BaseModel):
    type: Literal["thinking"] = "thinking"
    text: str


# Discriminated union of everything that can appear in a message's content.
Part = Annotated[
    TextPart | ImagePart | FilePart | ToolUsePart | ToolResultPart | ThinkingPart,
    Field(discriminator="type"),
]


class Message(BaseModel):
    """One conversation turn: a role plus an ordered list of content parts.

    Always a list of parts internally (even for plain text) so adapters have a
    single shape to translate. Use the constructors below for the common cases.
    """

    role: Role
    content: list[Part]

    @classmethod
    def user(cls, text: str) -> "Message":
        return cls(role=Role.USER, content=[TextPart(text=text)])

    @classmethod
    def assistant(cls, text: str) -> "Message":
        return cls(role=Role.ASSISTANT, content=[TextPart(text=text)])

    @property
    def text(self) -> str:
        """Concatenate all text parts (ignores images, tool calls, etc.)."""
        return "".join(part.text for part in self.content if isinstance(part, TextPart))
