"""Greenhouse and Zone CRUD endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.repositories.greenhouse_repository import GreenhouseRepository
from app.repositories.zone_repository import ZoneRepository
from app.schemas.plant_batches import (
    GreenhouseCreate,
    GreenhouseResponse,
    GreenhouseUpdate,
    ZoneCreate,
    ZoneResponse,
    ZoneUpdate,
)

router = APIRouter(prefix="/api/groups/{group_id}/greenhouses", tags=["greenhouses"])


# ---------------------------------------------------------------------------
# Greenhouse endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[GreenhouseResponse])
async def list_greenhouses(
    group_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[GreenhouseResponse]:
    """List greenhouses in a group."""
    repo = GreenhouseRepository(session)
    greenhouses = await repo.list(group_id=group_id)
    return [GreenhouseResponse.model_validate(gh) for gh in greenhouses]


@router.post("", response_model=GreenhouseResponse, status_code=201)
async def create_greenhouse(
    group_id: UUID,
    body: GreenhouseCreate,
    session: AsyncSession = Depends(get_db_session),
) -> GreenhouseResponse:
    """Create a new greenhouse within a group."""
    repo = GreenhouseRepository(session)
    greenhouse = await repo.create(
        group_id=group_id,
        name=body.name,
        location=body.location,
        description=body.description,
    )
    return GreenhouseResponse.model_validate(greenhouse)


@router.get("/{greenhouse_id}", response_model=GreenhouseResponse)
async def get_greenhouse(
    group_id: UUID,
    greenhouse_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> GreenhouseResponse:
    """Get greenhouse details."""
    repo = GreenhouseRepository(session)
    greenhouse = await repo.get_by_id(greenhouse_id)
    if greenhouse is None or greenhouse.group_id != group_id:
        raise HTTPException(status_code=404, detail="Greenhouse not found")
    return GreenhouseResponse.model_validate(greenhouse)


@router.patch("/{greenhouse_id}", response_model=GreenhouseResponse)
async def update_greenhouse(
    group_id: UUID,
    greenhouse_id: UUID,
    body: GreenhouseUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> GreenhouseResponse:
    """Update greenhouse metadata."""
    repo = GreenhouseRepository(session)
    greenhouse = await repo.get_by_id(greenhouse_id)
    if greenhouse is None or greenhouse.group_id != group_id:
        raise HTTPException(status_code=404, detail="Greenhouse not found")
    update_data = body.model_dump(exclude_unset=True)
    updated = await repo.update(greenhouse_id, **update_data)
    return GreenhouseResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# Zone endpoints
# ---------------------------------------------------------------------------


@router.get("/{greenhouse_id}/zones", response_model=list[ZoneResponse])
async def list_zones(
    group_id: UUID,
    greenhouse_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[ZoneResponse]:
    """List zones in a greenhouse."""
    repo = ZoneRepository(session)
    zones = await repo.list(greenhouse_id=greenhouse_id)
    return [ZoneResponse.model_validate(z) for z in zones]


@router.post("/{greenhouse_id}/zones", response_model=ZoneResponse, status_code=201)
async def create_zone(
    group_id: UUID,
    greenhouse_id: UUID,
    body: ZoneCreate,
    session: AsyncSession = Depends(get_db_session),
) -> ZoneResponse:
    """Create a new zone within a greenhouse."""
    # Verify greenhouse exists and belongs to the group
    gh_repo = GreenhouseRepository(session)
    greenhouse = await gh_repo.get_by_id(greenhouse_id)
    if greenhouse is None or greenhouse.group_id != group_id:
        raise HTTPException(status_code=404, detail="Greenhouse not found")

    repo = ZoneRepository(session)
    zone = await repo.create(
        greenhouse_id=greenhouse_id,
        name=body.name,
        description=body.description,
    )
    return ZoneResponse.model_validate(zone)


@router.get(
    "/{greenhouse_id}/zones/{zone_id}",
    response_model=ZoneResponse,
)
async def get_zone(
    group_id: UUID,
    greenhouse_id: UUID,
    zone_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ZoneResponse:
    """Get zone details."""
    repo = ZoneRepository(session)
    zone = await repo.get_by_id(zone_id)
    if zone is None or zone.greenhouse_id != greenhouse_id:
        raise HTTPException(status_code=404, detail="Zone not found")
    return ZoneResponse.model_validate(zone)


@router.patch(
    "/{greenhouse_id}/zones/{zone_id}",
    response_model=ZoneResponse,
)
async def update_zone(
    group_id: UUID,
    greenhouse_id: UUID,
    zone_id: UUID,
    body: ZoneUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> ZoneResponse:
    """Update zone metadata."""
    repo = ZoneRepository(session)
    zone = await repo.get_by_id(zone_id)
    if zone is None or zone.greenhouse_id != greenhouse_id:
        raise HTTPException(status_code=404, detail="Zone not found")
    update_data = body.model_dump(exclude_unset=True)
    updated = await repo.update(zone_id, **update_data)
    return ZoneResponse.model_validate(updated)
