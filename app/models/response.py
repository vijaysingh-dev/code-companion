from enum import Enum

from pydantic import BaseModel, Field

from app.core.constants import StreamEventType
from app.models.message import Part, Role, TextPart
from app.models.usage import Usage


class StopReason(str, Enum):
    """Normalized reason the model stopped, mapped from each provider's own enum.

    Anthropic `stop_reason`, OpenAI `finish_reason`, Gemini `finishReason` all
    collapse onto these.
    """

    END_TURN = "end_turn"  # natural completion
    MAX_TOKENS = "max_tokens"  # hit the output cap (truncated)
    TOOL_USE = "tool_use"  # wants a tool call — execute and continue
    STOP_SEQUENCE = "stop_sequence"  # hit a custom stop string
    REFUSAL = "refusal"  # safety refusal / filtered
    ERROR = "error"  # transport or provider error


class StreamEvent(BaseModel):
    """A single normalized streaming event — the unit the API layer turns into SSE.

    A flat shape (rather than a discriminated union) keeps the streaming hot path
    cheap and `model_dump_json()` trivial for SSE frames. Only the fields relevant
    to `type` are populated:

      MESSAGE_START   -> model
      TEXT_DELTA      -> text, index
      THINKING_DELTA  -> text, index
      TOOL_USE_START  -> tool_id, tool_name, index
      TOOL_USE_DELTA  -> tool_args_delta, index   (concatenated JSON string)
      TOOL_USE_STOP   -> index
      USAGE           -> usage
      STOP            -> stop_reason
      ERROR           -> error
      TITLE           -> title

    Tool-call contract: args always arrive as a concatenated JSON string across one
    or more TOOL_USE_DELTA events. Providers that return a whole object at once
    (Gemini) emit a single delta with the object dumped to JSON, so the accumulator
    stays uniform.
    """

    type: StreamEventType
    index: int | None = None  # content-block index within the message

    text: str | None = None  # TEXT_DELTA / THINKING_DELTA
    tool_id: str | None = None  # TOOL_USE_START
    tool_name: str | None = None  # TOOL_USE_START
    tool_args_delta: str | None = None  # TOOL_USE_DELTA (partial JSON)

    usage: Usage | None = None  # USAGE
    stop_reason: StopReason | None = None  # STOP
    model: str | None = None  # MESSAGE_START
    error: str | None = None  # ERROR
    title: str | None = None  # TITLE


class CompletionResponse(BaseModel):
    """The fully accumulated (non-streaming) result of a completion.

    Built by `BaseProvider.complete()` by folding the StreamEvent stream back into
    ordered content parts — the same shape a provider's non-streaming response would
    normalize to.
    """

    id: str | None = None
    model: str
    role: Role = Role.ASSISTANT
    content: list[Part] = Field(default_factory=list)
    stop_reason: StopReason | None = None
    usage: Usage = Field(default_factory=Usage)

    @property
    def text(self) -> str:
        return "".join(part.text for part in self.content if isinstance(part, TextPart))
