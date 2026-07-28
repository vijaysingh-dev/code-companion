from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import Effort


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1)
    context: str | None = None
    # Optional per-turn model override; None => keep the session's current model.
    provider: str | None = None
    model: str | None = None
    effort: Effort | None = None


class ModelInfo(BaseModel):
    provider: str
    provider_name: str
    model: str
    supports_effort: bool


class ModelsResponse(BaseModel):
    models: list[ModelInfo]


class CreateSessionRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    title: str | None = None


class UpdateSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class SessionInfo(BaseModel):
    id: str
    provider: str
    model: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class SessionsResponse(BaseModel):
    sessions: list[SessionInfo]


class MessageInfo(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class SessionDetail(SessionInfo):
    messages: list[MessageInfo]


class HealthResponse(BaseModel):
    status: str
    version: str
