"""Async CRUD repository for GreenhouseGroup."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import GreenhouseGroup


class GroupRepository:
    """Repository for greenhouse group CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, name: str, location: str | None = None, description: str | None = None) -> GreenhouseGroup:
        """Create a new greenhouse group."""
        group = GreenhouseGroup(
            name=name,
            location=location,
            description=description,
        )
        self.session.add(group)
        await self.session.flush()
        return group

    async def get_by_id(self, group_id: uuid.UUID) -> GreenhouseGroup | None:
        """Fetch a single group by its UUID."""
        return await self.session.get(GreenhouseGroup, group_id)

    async def list(self, **filters: Any) -> list[GreenhouseGroup]:
        """List groups, optionally filtered by keyword arguments."""
        stmt = select(GreenhouseGroup)
        for key, value in filters.items():
            if hasattr(GreenhouseGroup, key):
                stmt = stmt.where(getattr(GreenhouseGroup, key) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, group_id: uuid.UUID, **kwargs: Any) -> GreenhouseGroup | None:
        """Update fields on an existing group."""
        group = await self.session.get(GreenhouseGroup, group_id)
        if group is None:
            return None
        for key, value in kwargs.items():
            if hasattr(GreenhouseGroup, key):
                setattr(group, key, value)
        await self.session.flush()
        return group

    async def delete(self, group_id: uuid.UUID) -> bool:
        """Delete a group by UUID. Returns True if found and deleted."""
        group = await self.session.get(GreenhouseGroup, group_id)
        if group is None:
            return False
        await self.session.delete(group)
        await self.session.flush()
        return True
