from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Project root (the `code-companion/` directory). This file lives at
# app/core/constants.py, so three parents up is the repo root. Import BASE_DIR
# from here everywhere instead of recomputing paths.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class AppMode(str, Enum):
    """Which entrypoint started the process.

    Shared by one `Application` class: the FastAPI app runs as `APP` (needs the
    outbound HTTP client for LLM calls), the admin CLI runs as `CLI` (DB only,
    plain stderr logging). Gates logging setup and which subsystems start.
    """

    APP = "app"
    CLI = "cli"


class LLMProvider(str, Enum):
    """Canonical provider identifiers.

    Shared by `app.core.config` (settings validation) and `app.llm` (the factory
    that picks an adapter). `google` maps to the Gemini adapter and `llama` to the
    OpenAI adapter (OpenAI-compatible wire format, different base URL), so the set
    of *identifiers* is wider than the set of *adapters*.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LLAMA = "llama"


class Effort(str, Enum):
    """Normalized reasoning/effort level, chosen by the client per request.

    Crosses the backend boundary: the extension sends one of these on `ChatRequest`
    and each provider adapter translates it to that provider's native mechanism
    (OpenAI `reasoning_effort`, Anthropic `output_config.effort`, ...). It replaces
    per-request temperature for the main tier, whose frontier models reject sampling
    params but expose an effort control instead.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAX = "max"


class StreamEventType(str, Enum):
    """Normalized streaming event kinds emitted by every provider adapter.

    Lives in core constants because it crosses the backend boundary: the API layer
    re-serializes these as SSE frames (`event: <value>`) and the extension frontend
    switches on the same strings. Provider-specific wire events are translated into
    exactly this vocabulary inside `app/llm/providers/`.
    """

    MESSAGE_START = "message_start"
    TEXT_DELTA = "text_delta"
    THINKING_DELTA = "thinking_delta"
    TOOL_USE_START = "tool_use_start"
    TOOL_USE_DELTA = "tool_use_delta"
    TOOL_USE_STOP = "tool_use_stop"
    USAGE = "usage"
    STOP = "stop"
    ERROR = "error"
    DONE = "done"
