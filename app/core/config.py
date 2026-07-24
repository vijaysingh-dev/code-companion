from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.constants import BASE_DIR

_DEFAULT_DB_PATH = BASE_DIR / "companion.db"


class Settings(BaseSettings):
    """App/infra config from .env. LLM/model config lives in config.yaml (see catalog)."""

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

    # Blank by default so unrelated startup works; required to issue/verify tokens.
    SECRET_KEY: str = Field(default="")
    TOKEN_TTL_DAYS: int = Field(default=30)

    DATABASE_URL: str = Field(default=f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}")

    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(default=["*"])

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
