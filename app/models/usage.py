from pydantic import BaseModel


class Usage(BaseModel):
    """Normalized token accounting, provider-agnostic.

    Each provider reports usage under different names — Anthropic
    `input_tokens`/`output_tokens` (+ `cache_*`), OpenAI
    `prompt_tokens`/`completion_tokens`, Gemini
    `promptTokenCount`/`candidatesTokenCount` — and every adapter maps onto these.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    thinking_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def merge(self, other: "Usage") -> "Usage":
        """Sum two usage records (e.g. across multiple requests in an agent loop).

        Note: within a *single* streamed response, providers report cumulative
        totals, so the accumulator takes the last USAGE event rather than merging.
        """
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
            thinking_tokens=self.thinking_tokens + other.thinking_tokens,
        )
