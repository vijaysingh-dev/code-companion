import re
from pathlib import Path
from typing import Any

from app.core.constants import BASE_DIR
from app.models.prompt import PromptFile, ToolPromptFile
from app.models.tool import Tool

# Prompts live under the llm package as versioned JSON. Located via BASE_DIR per
# the repo convention (never recompute paths with Path(__file__)).
PROMPTS_DIR = BASE_DIR / "app" / "llm" / "prompts"
TOOL_PROMPTS_DIR = PROMPTS_DIR / "tool"

# Variable placeholders look like `{{ name }}` — brace-tolerant so prompt bodies
# can contain code/JSON literally. Unknown variables render as empty strings.
_VAR = re.compile(r"{{\s*(\w+)\s*}}")


def _render(template: str, variables: dict[str, Any]) -> str:
    return _VAR.sub(lambda m: str(variables.get(m.group(1), "")), template)


class PromptManager:
    """Loads and renders versioned JSON prompts, and builds tool definitions.

    File reads are cached; call `clear_cache()` after editing a prompt on disk to
    pick up changes without a restart.
    """

    def __init__(self, prompts_dir: Path = PROMPTS_DIR, tool_dir: Path = TOOL_PROMPTS_DIR) -> None:
        self._dir = prompts_dir
        self._tool_dir = tool_dir
        self._cache: dict[str, PromptFile] = {}
        self._tool_cache: dict[str, ToolPromptFile] = {}

    def _load(self, name: str) -> PromptFile:
        if name not in self._cache:
            path = self._dir / f"{name}.json"
            self._cache[name] = PromptFile.model_validate_json(path.read_text(encoding="utf-8"))
        return self._cache[name]

    def _load_tool(self, name: str) -> ToolPromptFile:
        if name not in self._tool_cache:
            path = self._tool_dir / f"{name}.json"
            self._tool_cache[name] = ToolPromptFile.model_validate_json(path.read_text(encoding="utf-8"))
        return self._tool_cache[name]

    def get(self, name: str, version: str | None = None) -> str:
        """Return the raw template for a prompt (latest version unless pinned)."""
        prompt = self._load(name)
        return prompt.versions[version or prompt.latest].template

    def render(self, name: str, version: str | None = None, **variables: Any) -> str:
        """Return the prompt with `{{ var }}` placeholders substituted."""
        return _render(self.get(name, version), variables)

    def tool_definition(self, name: str, version: str | None = None) -> Tool:
        """Build the normalized `Tool` schema from a tool prompt file."""
        tool = self._load_tool(name)
        version_data = tool.versions[version or tool.latest]
        return Tool(name=tool.name, description=version_data.description, parameters=version_data.parameters)

    def clear_cache(self) -> None:
        self._cache.clear()
        self._tool_cache.clear()


# Process-wide default manager.
prompts = PromptManager()
