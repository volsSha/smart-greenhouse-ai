"""Async CRUD repository for GreenhouseZone."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone import GreenhouseZone


class ZoneRepository:
    """Repository for greenhouse zone CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        greenhouse_id: uuid.UUID,
        name: str,
        description: str | None = None,
        source_type: str = "real",
        simulator_managed: bool = False,
    ) -> GreenhouseZone:
        """Create a new zone."""
        zone = GreenhouseZone(
            greenhouse_id=greenhouse_id,
            name=name,
            description=description,
            source_type=source_type,
            simulator_managed=simulator_managed,
        )
        self.session.add(zone)
        await self.session.flush()
        return zone

    async def get_by_id(self, zone_id: uuid.UUID) -> GreenhouseZone | None:
        """Fetch a single zone by its UUID."""
        return await self.session.get(GreenhouseZone, zone_id)

    async def list(self, **filters: Any) -> list[GreenhouseZone]:
        """List zones, optionally filtered by keyword arguments."""
        stmt = select(GreenhouseZone)
        for key, value in filters.items():
            if hasattr(GreenhouseZone, key):
                stmt = stmt.where(getattr(GreenhouseZone, key) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, zone_id: uuid.UUID, **kwargs: Any) -> GreenhouseZone | None:
        """Update fields on an existing zone."""
        zone = await self.session.get(GreenhouseZone, zone_id)
        if zone is None:
            return None
        for key, value in kwargs.items():
            if hasattr(GreenhouseZone, key):
                setattr(zone, key, value)
        await self.session.flush()
        return zone

    async def delete(self, zone_id: uuid.UUID) -> bool:
        """Delete a zone by UUID. Returns True if found and deleted."""
        zone = await self.session.get(GreenhouseZone, zone_id)
        if zone is None:
            return False
        await self.session.delete(zone)
        await self.session.flush()
        return True
