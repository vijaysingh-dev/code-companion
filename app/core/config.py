from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.constants import LLMProvider

# Recommended model per provider, used when the matching *_MODEL is left blank.
# Pin a specific model in .env to override.
_DEFAULT_MODEL: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "gpt-4o",
    LLMProvider.ANTHROPIC: "claude-opus-4-8",
    LLMProvider.GOOGLE: "gemini-2.5-pro",
    LLMProvider.LLAMA: "llama-3.3-70b-instruct",
}
_DEFAULT_MINI_MODEL: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "gpt-4o-mini",
    LLMProvider.ANTHROPIC: "claude-haiku-4-5",
    LLMProvider.GOOGLE: "gemini-2.5-flash",
    LLMProvider.LLAMA: "llama-3.1-8b-instruct",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "Code Companion"
    APP_VERSION: str = "0.1.0"
    DESCRIPTION: str = "AI coding assistant backend"
    DEBUG: bool = Field(default=False, description="Enable debug mode")

    PORT: int = Field(default=8000)

    API_PREFIX: str = "/api"
    LOG_LEVEL: str = Field(default="INFO")

    # NoDecode: keep pydantic-settings from JSON-decoding the dotenv value, so the
    # validator below receives the raw comma-separated string.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(default=["*"])

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    # Two model tiers (roadmap Phase 3 — model tiering):
    #   LLM_*       = the main model: reasoning, planning, code edits.
    #   MINI_LLM_* = the cheap/fast model for grunt steps: search, summarize, classify.
    # Each tier picks one of the four providers and carries its own model, so the
    # mini tier can even run on a different provider than the main one.
    #
    # Field notes shared by both tiers:
    #   *_MODEL       — leave blank to use the recommended model for that provider
    #                   (see _DEFAULT_MODEL / _DEFAULT_MINI_MODEL); set to pin one.
    #   *_BASE_URL    — optional; needed for self-hosted / OpenAI-compatible endpoints
    #                   (llama via Ollama/Together/Groq, google via an OpenAI-compat proxy).
    #
    # Temperature is a mini-tier-only setting (MINI_LLM_TEMPERATURE below). The main tier
    # has no temperature knob because it's meant for frontier/reasoning models (gpt-5.1,
    # Opus 4.7+, Sonnet 5) that reject the parameter; the mini tier runs smaller models
    # (gpt-4o-mini, haiku, gemini-flash, llama) that accept it. A main-tier model that
    # still wants one can be handed it through `CompletionRequest.extra`.
    LLM_PROVIDER: LLMProvider = Field(default=LLMProvider.OPENAI)
    LLM_BASE_URL: str = Field(default="")
    LLM_MODEL: str = Field(default="")
    LLM_API_KEY: str = Field(default="")
    LLM_MAX_TOKENS: int = Field(default=2048)

    # The mini tier reuses the main connection (provider + endpoint + key) unless
    # overridden, but keeps its own model and generation params — the point is a
    # cheaper/lighter model, optionally on a different provider/account.
    MINI_LLM_PROVIDER: LLMProvider | None = None
    MINI_LLM_BASE_URL: str | None = None
    MINI_LLM_MODEL: str = Field(default="")
    MINI_LLM_API_KEY: str | None = None
    MINI_LLM_TEMPERATURE: float | None = Field(default=None)
    MINI_LLM_MAX_TOKENS: int = Field(default=1024)

    @field_validator("MINI_LLM_PROVIDER", "MINI_LLM_TEMPERATURE", mode="before")
    @classmethod
    def _blank_to_none(cls, v: object) -> object:
        """Treat a blank .env entry (`MINI_LLM_TEMPERATURE=`) as unset rather than "".

        Without this, an empty string reaches enum/float parsing and fails, so the
        documented "leave blank for the default" would break startup.
        """
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @model_validator(mode="after")
    def _resolve_llm_tiers(self) -> "Settings":
        """Resolve the mini tier's provider/connection/model from the main tier.

        The mini tier defaults to the main provider. Its key/endpoint are inherited
        from the main tier only when it runs on the *same* provider — a different
        provider needs its own credentials, so those stay as set (or blank). A blank
        model on either tier resolves to that provider's recommended default.
        """
        mini_provider: LLMProvider = self.MINI_LLM_PROVIDER or self.LLM_PROVIDER
        self.MINI_LLM_PROVIDER = mini_provider
        if mini_provider == self.LLM_PROVIDER:
            if not self.MINI_LLM_API_KEY:
                self.MINI_LLM_API_KEY = self.LLM_API_KEY
            if not self.MINI_LLM_BASE_URL:
                self.MINI_LLM_BASE_URL = self.LLM_BASE_URL
        if not self.LLM_MODEL:
            self.LLM_MODEL = _DEFAULT_MODEL[self.LLM_PROVIDER]
        if not self.MINI_LLM_MODEL:
            self.MINI_LLM_MODEL = _DEFAULT_MINI_MODEL[mini_provider]
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
