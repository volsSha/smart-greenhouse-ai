"""Persisted alert endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.repositories.alert_repository import AlertRepository
from app.schemas.alerts import AlertResponse, AlertUpdate

router = APIRouter(prefix="/api/groups/{group_id}/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    group_id: UUID,
    status: str = Query("active", pattern="^(active|dismissed|resolved)$"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> list[AlertResponse]:
    repo = AlertRepository(session)
    alerts = await repo.list_by_group(group_id, status=status)
    return [AlertResponse.model_validate(alert) for alert in alerts[:limit]]


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    group_id: UUID,
    alert_id: UUID,
    body: AlertUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> AlertResponse:
    repo = AlertRepository(session)
    alert = await repo.get_by_id(alert_id)
    if alert is None or alert.group_id != group_id:
        raise HTTPException(status_code=404, detail="Alert not found")

    updated = await repo.update(alert_id, status=body.status)
    await session.commit()
    return AlertResponse.model_validate(updated)
