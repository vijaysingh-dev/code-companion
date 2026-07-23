from pydantic import BaseModel, Field

from app.core.constants import Effort


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    # Optional caller-supplied context, e.g. the open file or selection.
    context: str | None = None
    # Optional per-request overrides; None => server default (from settings). `model` is
    # validated against the configured provider's catalog; `effort` is the main-tier
    # reasoning control (translated per provider).
    model: str | None = None
    effort: Effort | None = None


class ChatResponse(BaseModel):
    content: str


class ModelInfo(BaseModel):
    id: str
    # Whether this model honours the `effort` control (frontier/reasoning models do).
    supports_effort: bool
    # The currently configured main model.
    default: bool


class ModelsResponse(BaseModel):
    provider: str
    models: list[ModelInfo]


class HealthResponse(BaseModel):
    status: str
    version: str
