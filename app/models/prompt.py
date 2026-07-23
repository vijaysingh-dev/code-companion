from typing import Any

from pydantic import BaseModel, Field


class PromptVersion(BaseModel):
    """One immutable version of a prompt template."""

    template: str
    notes: str | None = None


class PromptFile(BaseModel):
    """On-disk shape of a prompt JSON file (`app/llm/prompts/<name>.json`).

    Keeping every version in one file lets prompts be iterated and rolled back
    without losing history — `latest` names the default version to serve.
    """

    name: str
    description: str | None = None
    latest: str
    versions: dict[str, PromptVersion]


class ToolPromptVersion(BaseModel):
    """One version of a tool's model-facing definition (description + schema)."""

    description: str
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})
    notes: str | None = None


class ToolPromptFile(BaseModel):
    """On-disk shape of a tool prompt file (`app/llm/prompts/tool/<name>.json`).

    The description and parameter JSON schema are the model-facing half of a tool;
    the executor lives in `app/llm/tools/<name>.py` and is bound by matching `name`.
    """

    name: str
    description: str | None = None
    latest: str
    versions: dict[str, ToolPromptVersion]
