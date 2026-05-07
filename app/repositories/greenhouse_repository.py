"""Async CRUD repository for Greenhouse."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.greenhouse import Greenhouse


class GreenhouseRepository:
    """Repository for greenhouse CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        group_id: uuid.UUID,
        name: str,
        location: str | None = None,
        description: str | None = None,
    ) -> Greenhouse:
        """Create a new greenhouse."""
        greenhouse = Greenhouse(
            group_id=group_id,
            name=name,
            location=location,
            description=description,
        )
        self.session.add(greenhouse)
        await self.session.flush()
        return greenhouse

    async def get_by_id(self, greenhouse_id: uuid.UUID) -> Greenhouse | None:
        """Fetch a single greenhouse by its UUID."""
        return await self.session.get(Greenhouse, greenhouse_id)

    async def list(self, **filters: Any) -> list[Greenhouse]:
        """List greenhouses, optionally filtered by keyword arguments."""
        stmt = select(Greenhouse)
        for key, value in filters.items():
            if hasattr(Greenhouse, key):
                stmt = stmt.where(getattr(Greenhouse, key) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, greenhouse_id: uuid.UUID, **kwargs: Any) -> Greenhouse | None:
        """Update fields on an existing greenhouse."""
        greenhouse = await self.session.get(Greenhouse, greenhouse_id)
        if greenhouse is None:
            return None
        for key, value in kwargs.items():
            if hasattr(Greenhouse, key):
                setattr(greenhouse, key, value)
        await self.session.flush()
        return greenhouse

    async def delete(self, greenhouse_id: uuid.UUID) -> bool:
        """Delete a greenhouse by UUID. Returns True if found and deleted."""
        greenhouse = await self.session.get(Greenhouse, greenhouse_id)
        if greenhouse is None:
            return False
        await self.session.delete(greenhouse)
        await self.session.flush()
        return True
