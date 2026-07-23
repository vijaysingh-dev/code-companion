import logging

from app.llm.tools.base import BaseTool
from app.models.message import ToolResultPart, ToolUsePart
from app.models.tool import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Holds the available tools and dispatches model tool calls to them."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def definitions(self) -> list[Tool]:
        """Tool schemas to attach to a CompletionRequest."""
        return [tool.definition() for tool in self._tools.values()]

    async def run(self, call: ToolUsePart) -> ToolResultPart:
        """Execute one tool call and wrap the outcome as a ToolResultPart.

        `call.id` is the provider correlation id (the tool name for Gemini, which
        has no call id). Any tool exception is surfaced to the model as an error
        result rather than raised, so the agent loop can recover.
        """
        tool_use_id = call.id or call.name
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResultPart(tool_use_id=tool_use_id, content=f"unknown tool: {call.name}", is_error=True)
        try:
            result = await tool.run(call.args)
        except Exception as exc:  # noqa: BLE001 - surface any tool failure back to the model
            logger.exception("tool %s failed", call.name)
            return ToolResultPart(tool_use_id=tool_use_id, content=str(exc), is_error=True)
        return ToolResultPart(tool_use_id=tool_use_id, content=result)
