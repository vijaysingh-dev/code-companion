from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    # Optional caller-supplied context, e.g. the open file or selection.
    context: str | None = None


class ChatResponse(BaseModel):
    content: str


class HealthResponse(BaseModel):
    status: str
    version: str
