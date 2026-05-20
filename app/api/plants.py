"""Plant batch and plant profile CRUD endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.repositories.greenhouse_repository import GreenhouseRepository
from app.repositories.plant_batch_repository import (
    PlantBatchRepository,
    PlantProfileRepository,
)
from app.repositories.zone_repository import ZoneRepository
from app.schemas.plant_batches import (
    PlantBatchCreate,
    PlantBatchResponse,
    PlantBatchUpdate,
    PlantProfileCreate,
    PlantProfileResponse,
    PlantProfileUpdate,
)

router = APIRouter(tags=["plants"])


# ---------------------------------------------------------------------------
# Plant Batch endpoints (scoped under a group)
# ---------------------------------------------------------------------------


@router.get(
    "/api/groups/{group_id}/plant-batches",
    response_model=list[PlantBatchResponse],
)
async def list_plant_batches(
    group_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[PlantBatchResponse]:
    """List all plant batches across all zones in a group.

    Returns batches for every zone in every greenhouse belonging to the group.
    """
    gh_repo = GreenhouseRepository(session)
    greenhouses = await gh_repo.list(group_id=group_id)

    zone_repo = ZoneRepository(session)
    batch_repo = PlantBatchRepository(session)

    all_batches: list[PlantBatchResponse] = []
    for greenhouse in greenhouses:
        zones = await zone_repo.list(greenhouse_id=greenhouse.id)
        for zone in zones:
            batches = await batch_repo.list_by_zone(zone.id)
            all_batches.extend(
                PlantBatchResponse.model_validate(b) for b in batches
            )
    return all_batches


@router.post(
    "/api/groups/{group_id}/plant-batches",
    response_model=PlantBatchResponse,
    status_code=201,
)
async def create_plant_batch(
    group_id: UUID,
    body: PlantBatchCreate,
    session: AsyncSession = Depends(get_db_session),
) -> PlantBatchResponse:
    """Create a new plant batch in a zone belonging to the group."""
    # Verify the zone belongs to a greenhouse in this group
    zone_repo = ZoneRepository(session)
    zone = await zone_repo.get_by_id(body.zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")

    gh_repo = GreenhouseRepository(session)
    greenhouse = await gh_repo.get_by_id(zone.greenhouse_id)
    if greenhouse is None or greenhouse.group_id != group_id:
        raise HTTPException(status_code=404, detail="Zone not found in this group")

    if body.profile_id is not None:
        profile_repo = PlantProfileRepository(session)
        profile = await profile_repo.get_by_id(body.profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Plant profile not found")

    batch_repo = PlantBatchRepository(session)
    batch = await batch_repo.create(
        zone_id=body.zone_id,
        profile_id=body.profile_id,
        name=body.name,
        species=body.species,
        cultivar=body.cultivar,
        planted_at=body.planted_at,
        growth_stage=body.growth_stage,
        notes=body.notes,
    )
    await session.commit()
    return PlantBatchResponse.model_validate(batch)


@router.get(
    "/api/groups/{group_id}/plant-batches/{batch_id}",
    response_model=PlantBatchResponse,
)
async def get_plant_batch(
    group_id: UUID,
    batch_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> PlantBatchResponse:
    """Get plant batch details."""
    batch_repo = PlantBatchRepository(session)
    batch = await batch_repo.get_by_id(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Plant batch not found")

    # Verify the batch's zone belongs to this group
    zone_repo = ZoneRepository(session)
    zone = await zone_repo.get_by_id(batch.zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Plant batch not found")

    gh_repo = GreenhouseRepository(session)
    greenhouse = await gh_repo.get_by_id(zone.greenhouse_id)
    if greenhouse is None or greenhouse.group_id != group_id:
        raise HTTPException(status_code=404, detail="Plant batch not found")

    return PlantBatchResponse.model_validate(batch)


@router.patch(
    "/api/groups/{group_id}/plant-batches/{batch_id}",
    response_model=PlantBatchResponse,
)
async def update_plant_batch(
    group_id: UUID,
    batch_id: UUID,
    body: PlantBatchUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> PlantBatchResponse:
    """Update plant batch metadata."""
    batch_repo = PlantBatchRepository(session)
    batch = await batch_repo.get_by_id(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Plant batch not found")

    # Verify the batch's zone belongs to this group
    zone_repo = ZoneRepository(session)
    zone = await zone_repo.get_by_id(batch.zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Plant batch not found")

    gh_repo = GreenhouseRepository(session)
    greenhouse = await gh_repo.get_by_id(zone.greenhouse_id)
    if greenhouse is None or greenhouse.group_id != group_id:
        raise HTTPException(status_code=404, detail="Plant batch not found")

    update_data = body.model_dump(exclude_unset=True)
    if "profile_id" in update_data and update_data["profile_id"] is not None:
        profile_repo = PlantProfileRepository(session)
        profile = await profile_repo.get_by_id(update_data["profile_id"])
        if profile is None:
            raise HTTPException(status_code=404, detail="Plant profile not found")

    updated = await batch_repo.update(batch_id, **update_data)
    await session.commit()
    return PlantBatchResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# Plant Profile endpoints (global, not group-scoped)
# ---------------------------------------------------------------------------


@router.get(
    "/api/plant-profiles",
    response_model=list[PlantProfileResponse],
)
async def list_plant_profiles(
    session: AsyncSession = Depends(get_db_session),
) -> list[PlantProfileResponse]:
    """List all reusable plant profiles."""
    repo = PlantProfileRepository(session)
    profiles = await repo.list()
    return [PlantProfileResponse.model_validate(p) for p in profiles]


@router.post(
    "/api/plant-profiles",
    response_model=PlantProfileResponse,
    status_code=201,
)
async def create_plant_profile(
    body: PlantProfileCreate,
    session: AsyncSession = Depends(get_db_session),
) -> PlantProfileResponse:
    """Create a new plant profile."""
    repo = PlantProfileRepository(session)
    profile = await repo.create(**body.model_dump())
    await session.commit()
    return PlantProfileResponse.model_validate(profile)


@router.get(
    "/api/plant-profiles/{profile_id}",
    response_model=PlantProfileResponse,
)
async def get_plant_profile(
    profile_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> PlantProfileResponse:
    """Get a single reusable plant profile."""
    repo = PlantProfileRepository(session)
    profile = await repo.get_by_id(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Plant profile not found")
    return PlantProfileResponse.model_validate(profile)


@router.patch(
    "/api/plant-profiles/{profile_id}",
    response_model=PlantProfileResponse,
)
async def update_plant_profile(
    profile_id: UUID,
    body: PlantProfileUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> PlantProfileResponse:
    """Update a reusable plant profile."""
    repo = PlantProfileRepository(session)
    profile = await repo.update(profile_id, **body.model_dump(exclude_unset=True))
    if profile is None:
        raise HTTPException(status_code=404, detail="Plant profile not found")
    await session.commit()
    return PlantProfileResponse.model_validate(profile)
