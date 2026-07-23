from app.llm.tools.base import BaseTool
from app.llm.tools.read_file import ReadFileTool
from app.llm.tools.registry import ToolRegistry


def build_registry() -> ToolRegistry:
    """Construct a registry with the built-in tools registered."""
    registry = ToolRegistry()
    registry.register(ReadFileTool())
    return registry


__all__ = ["BaseTool", "ReadFileTool", "ToolRegistry", "build_registry"]
