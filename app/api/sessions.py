import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import authenticated
from app.api.deps import get_db
from app.models.schema import (
    CreateSessionRequest,
    MessageInfo,
    SessionDetail,
    SessionInfo,
    SessionsResponse,
    UpdateSessionRequest,
)
from app.models.tables import ChatSession, SessionMessage
from app.services import catalog
from app.services.session import SessionService

logger = logging.getLogger(__name__)

router = APIRouter()


def _info(row: ChatSession) -> SessionInfo:
    return SessionInfo(
        id=row.id,
        provider=row.provider,
        model=row.model,
        title=row.title,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _message_info(row: SessionMessage) -> MessageInfo:
    text = "".join(part.get("text", "") for part in row.content if part.get("type") == "text")
    return MessageInfo(id=row.id, role=row.role, content=text, created_at=row.created_at)


@router.post("")
@authenticated
async def create_session(
    request: Request,
    body: CreateSessionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionInfo:
    resolved = catalog.resolve(body.provider, body.model)
    row = await SessionService(db).create(request.state.user_id, resolved.provider.value, resolved.model, body.title)
    return _info(row)


@router.get("")
@authenticated
async def list_sessions(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> SessionsResponse:
    rows = await SessionService(db).list_all(request.state.user_id)
    return SessionsResponse(sessions=[_info(row) for row in rows])


@router.get("/{session_id}")
@authenticated
async def get_session(
    request: Request,
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionDetail:
    service = SessionService(db)
    row = await service.get(request.state.user_id, session_id)
    messages = await service.rows(session_id)
    info: dict[str, Any] = _info(row).model_dump()
    return SessionDetail(**info, messages=[_message_info(m) for m in messages])


@router.patch("/{session_id}")
@authenticated
async def update_session(
    request: Request,
    session_id: str,
    body: UpdateSessionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionInfo:
    row = await SessionService(db).update_title(request.state.user_id, session_id, body.title)
    return _info(row)


@router.delete("/{session_id}", status_code=204)
@authenticated
async def delete_session(
    request: Request,
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await SessionService(db).delete(request.state.user_id, session_id)
