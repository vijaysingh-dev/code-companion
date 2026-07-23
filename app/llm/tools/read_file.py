from pathlib import Path
from typing import Any

from app.core.constants import BASE_DIR
from app.llm.tools.base import BaseTool


class ReadFileTool(BaseTool):
    """Read a workspace file. Confined to `root` — traversal outside is rejected."""

    name = "read_file"

    def __init__(self, root: Path = BASE_DIR) -> None:
        self._root = root.resolve()

    async def run(self, args: dict[str, Any]) -> str:
        path = args["path"]
        if not isinstance(path, str):
            raise ValueError("'path' must be a string")
        target = (self._root / path).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError(f"path escapes workspace root: {path}")
        if not target.is_file():
            raise FileNotFoundError(f"no such file: {path}")
        return target.read_text(encoding="utf-8")
