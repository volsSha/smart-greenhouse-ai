"""REST endpoints for persisted application debug logs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.repositories.debug_log_repository import DebugLogRepository

router = APIRouter(prefix="/api/debug-logs", tags=["debug-logs"])


class DebugLogResponse(BaseModel):
    """Persisted debug/error log entry."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    created_at: datetime
    level: str
    event_type: str
    component: str
    message: str
    path: str | None
    method: str | None
    status_code: int | None
    duration_ms: float | None
    request_id: str | None
    error_type: str | None
    stack_trace: str | None
    metadata: dict[str, Any] | None = Field(validation_alias="log_metadata")


@router.get("", response_model=list[DebugLogResponse])
async def list_debug_logs(
    level: str | None = None,
    component: str | None = None,
    event_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[DebugLogResponse]:
    """List newest persisted debug/error logs with optional filters."""
    repo = DebugLogRepository(session)
    logs = await repo.list(
        level=level,
        component=component,
        event_type=event_type,
        limit=limit,
    )
    return [DebugLogResponse.model_validate(log) for log in logs]
