"""Async CRUD repositories for PlantBatch and PlantProfile."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant_batch import PlantBatch, PlantProfile


class PlantBatchRepository:
    """Repository for plant batch CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        zone_id: uuid.UUID,
        name: str,
        profile_id: uuid.UUID | None = None,
        species: str | None = None,
        cultivar: str | None = None,
        planted_at: date | None = None,
        growth_stage: str | None = None,
        notes: str | None = None,
    ) -> PlantBatch:
        """Create a new plant batch."""
        batch = PlantBatch(
            zone_id=zone_id,
            profile_id=profile_id,
            name=name,
            species=species,
            cultivar=cultivar,
            planted_at=planted_at,
            growth_stage=growth_stage,
            notes=notes,
        )
        self.session.add(batch)
        await self.session.flush()
        return batch

    async def get_by_id(self, batch_id: uuid.UUID) -> PlantBatch | None:
        """Fetch a single plant batch by its UUID."""
        return await self.session.get(PlantBatch, batch_id)

    async def list(self, **filters: Any) -> list[PlantBatch]:
        """List plant batches, optionally filtered by keyword arguments."""
        stmt = select(PlantBatch)
        for key, value in filters.items():
            if hasattr(PlantBatch, key):
                stmt = stmt.where(getattr(PlantBatch, key) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_zone(self, zone_id: uuid.UUID) -> list[PlantBatch]:
        """List all plant batches for a specific zone."""
        return await self.list(zone_id=zone_id)

    async def update(self, batch_id: uuid.UUID, **kwargs: Any) -> PlantBatch | None:
        """Update fields on an existing plant batch."""
        batch = await self.session.get(PlantBatch, batch_id)
        if batch is None:
            return None
        for key, value in kwargs.items():
            if hasattr(PlantBatch, key):
                setattr(batch, key, value)
        await self.session.flush()
        return batch

    async def delete(self, batch_id: uuid.UUID) -> bool:
        """Delete a plant batch by UUID. Returns True if found and deleted."""
        batch = await self.session.get(PlantBatch, batch_id)
        if batch is None:
            return False
        await self.session.delete(batch)
        await self.session.flush()
        return True


class PlantProfileRepository:
    """Repository for plant profile CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        crop_name: str,
        growth_stage: str | None = None,
        temp_min: float | None = None,
        temp_opt: float | None = None,
        temp_max: float | None = None,
        humidity_min: float | None = None,
        humidity_opt: float | None = None,
        humidity_max: float | None = None,
        soil_moisture_min: float | None = None,
        soil_moisture_opt: float | None = None,
        soil_moisture_max: float | None = None,
        co2_min: float | None = None,
        co2_opt: float | None = None,
        co2_max: float | None = None,
        light_min: float | None = None,
        light_opt: float | None = None,
        light_max: float | None = None,
        description: str | None = None,
    ) -> PlantProfile:
        """Create a new plant profile."""
        profile = PlantProfile(
            crop_name=crop_name,
            growth_stage=growth_stage,
            temp_min=temp_min,
            temp_opt=temp_opt,
            temp_max=temp_max,
            humidity_min=humidity_min,
            humidity_opt=humidity_opt,
            humidity_max=humidity_max,
            soil_moisture_min=soil_moisture_min,
            soil_moisture_opt=soil_moisture_opt,
            soil_moisture_max=soil_moisture_max,
            co2_min=co2_min,
            co2_opt=co2_opt,
            co2_max=co2_max,
            light_min=light_min,
            light_opt=light_opt,
            light_max=light_max,
            description=description,
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def get_by_id(self, profile_id: uuid.UUID) -> PlantProfile | None:
        """Fetch a single plant profile by its UUID."""
        return await self.session.get(PlantProfile, profile_id)

    async def list(self, **filters: Any) -> list[PlantProfile]:
        """List plant profiles, optionally filtered by keyword arguments."""
        stmt = select(PlantProfile)
        for key, value in filters.items():
            if hasattr(PlantProfile, key):
                stmt = stmt.where(getattr(PlantProfile, key) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_crop_and_stage(
        self, crop_name: str, growth_stage: str | None = None
    ) -> PlantProfile | None:
        """Find a profile matching crop_name and optionally growth_stage."""
        stmt = select(PlantProfile).where(PlantProfile.crop_name == crop_name)
        if growth_stage is not None:
            stmt = stmt.where(PlantProfile.growth_stage == growth_stage)
        else:
            stmt = stmt.where(PlantProfile.growth_stage.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, profile_id: uuid.UUID, **kwargs: Any) -> PlantProfile | None:
        """Update fields on an existing plant profile."""
        profile = await self.session.get(PlantProfile, profile_id)
        if profile is None:
            return None
        for key, value in kwargs.items():
            if hasattr(PlantProfile, key):
                setattr(profile, key, value)
        await self.session.flush()
        return profile

    async def delete(self, profile_id: uuid.UUID) -> bool:
        """Delete a plant profile by UUID. Returns True if found and deleted."""
        profile = await self.session.get(PlantProfile, profile_id)
        if profile is None:
            return False
        await self.session.delete(profile)
        await self.session.flush()
        return True
