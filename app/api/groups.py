"""Group CRUD endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.repositories.group_repository import GroupRepository
from app.schemas.plant_batches import GroupCreate, GroupResponse, GroupUpdate

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    session: AsyncSession = Depends(get_db_session),
) -> list[GroupResponse]:
    """List all greenhouse groups."""
    repo = GroupRepository(session)
    groups = await repo.list()
    return [GroupResponse.model_validate(g) for g in groups]


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    body: GroupCreate,
    session: AsyncSession = Depends(get_db_session),
) -> GroupResponse:
    """Create a new greenhouse group."""
    repo = GroupRepository(session)
    group = await repo.create(
        name=body.name,
        location=body.location,
        description=body.description,
    )
    return GroupResponse.model_validate(group)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> GroupResponse:
    """Get group details by ID."""
    repo = GroupRepository(session)
    group = await repo.get_by_id(group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return GroupResponse.model_validate(group)


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID,
    body: GroupUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> GroupResponse:
    """Update group metadata."""
    repo = GroupRepository(session)
    update_data = body.model_dump(exclude_unset=True)
    group = await repo.update(group_id, **update_data)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return GroupResponse.model_validate(group)
