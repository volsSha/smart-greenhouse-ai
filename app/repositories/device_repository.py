"""Async CRUD repositories for EdgeNode, Sensor, and Actuator."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Actuator, EdgeNode, Sensor


class EdgeNodeRepository:
    """Repository for edge node CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        greenhouse_id: uuid.UUID,
        node_key: str,
        name: str,
        node_type: str,
        firmware_version: str | None = None,
    ) -> EdgeNode:
        """Create a new edge node."""
        node = EdgeNode(
            greenhouse_id=greenhouse_id,
            node_key=node_key,
            name=name,
            node_type=node_type,
            firmware_version=firmware_version,
        )
        self.session.add(node)
        await self.session.flush()
        return node

    async def get_by_id(self, node_id: uuid.UUID) -> EdgeNode | None:
        return await self.session.get(EdgeNode, node_id)

    async def get_by_node_key(self, node_key: str) -> EdgeNode | None:
        """Look up an edge node by its unique key."""
        stmt = select(EdgeNode).where(EdgeNode.node_key == node_key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, **filters: Any) -> list[EdgeNode]:
        stmt = select(EdgeNode)
        for key, value in filters.items():
            if hasattr(EdgeNode, key):
                stmt = stmt.where(getattr(EdgeNode, key) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, node_id: uuid.UUID, **kwargs: Any) -> EdgeNode | None:
        node = await self.session.get(EdgeNode, node_id)
        if node is None:
            return None
        for key, value in kwargs.items():
            if hasattr(EdgeNode, key):
                setattr(node, key, value)
        await self.session.flush()
        return node

    async def delete(self, node_id: uuid.UUID) -> bool:
        node = await self.session.get(EdgeNode, node_id)
        if node is None:
            return False
        await self.session.delete(node)
        await self.session.flush()
        return True


class SensorRepository:
    """Repository for sensor CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        zone_id: uuid.UUID,
        sensor_key: str,
        metric: str,
        unit: str | None = None,
        edge_node_id: uuid.UUID | None = None,
        is_active: bool = True,
    ) -> Sensor:
        """Create a new sensor."""
        sensor = Sensor(
            zone_id=zone_id,
            sensor_key=sensor_key,
            metric=metric,
            unit=unit,
            edge_node_id=edge_node_id,
            is_active=is_active,
        )
        self.session.add(sensor)
        await self.session.flush()
        return sensor

    async def get_by_id(self, sensor_id: uuid.UUID) -> Sensor | None:
        return await self.session.get(Sensor, sensor_id)

    async def list(self, **filters: Any) -> list[Sensor]:
        stmt = select(Sensor)
        for key, value in filters.items():
            if hasattr(Sensor, key):
                stmt = stmt.where(getattr(Sensor, key) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, sensor_id: uuid.UUID, **kwargs: Any) -> Sensor | None:
        sensor = await self.session.get(Sensor, sensor_id)
        if sensor is None:
            return None
        for key, value in kwargs.items():
            if hasattr(Sensor, key):
                setattr(sensor, key, value)
        await self.session.flush()
        return sensor

    async def delete(self, sensor_id: uuid.UUID) -> bool:
        sensor = await self.session.get(Sensor, sensor_id)
        if sensor is None:
            return False
        await self.session.delete(sensor)
        await self.session.flush()
        return True


class ActuatorRepository:
    """Repository for actuator CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        zone_id: uuid.UUID,
        actuator_key: str,
        actuator_type: str,
        unit: str | None = None,
        edge_node_id: uuid.UUID | None = None,
        is_active: bool = True,
    ) -> Actuator:
        """Create a new actuator."""
        actuator = Actuator(
            zone_id=zone_id,
            actuator_key=actuator_key,
            actuator_type=actuator_type,
            edge_node_id=edge_node_id,
            is_active=is_active,
        )
        self.session.add(actuator)
        await self.session.flush()
        return actuator

    async def get_by_id(self, actuator_id: uuid.UUID) -> Actuator | None:
        return await self.session.get(Actuator, actuator_id)

    async def list(self, **filters: Any) -> list[Actuator]:
        stmt = select(Actuator)
        for key, value in filters.items():
            if hasattr(Actuator, key):
                stmt = stmt.where(getattr(Actuator, key) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, actuator_id: uuid.UUID, **kwargs: Any) -> Actuator | None:
        actuator = await self.session.get(Actuator, actuator_id)
        if actuator is None:
            return None
        for key, value in kwargs.items():
            if hasattr(Actuator, key):
                setattr(actuator, key, value)
        await self.session.flush()
        return actuator

    async def delete(self, actuator_id: uuid.UUID) -> bool:
        actuator = await self.session.get(Actuator, actuator_id)
        if actuator is None:
            return False
        await self.session.delete(actuator)
        await self.session.flush()
        return True
