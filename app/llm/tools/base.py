from abc import ABC, abstractmethod
from typing import Any

from app.llm.prompt import prompts
from app.models.tool import Tool


class BaseTool(ABC):
    """A client-side tool: a name, a model-facing definition, and an executor.

    The definition (description + parameter schema) is loaded from the tool's
    prompt file (`app/llm/prompts/tool/<name>.json`); only the behavior lives here.
    Args arrive as a dict (the model's parsed tool input), so subclasses read what
    they need from it rather than declaring positional parameters.
    """

    name: str
    version: str | None = None  # pin a tool-prompt version, or None for latest

    @abstractmethod
    async def run(self, args: dict[str, Any]) -> str:
        """Execute the tool and return its result as text."""

    def definition(self) -> Tool:
        return prompts.tool_definition(self.name, self.version)
