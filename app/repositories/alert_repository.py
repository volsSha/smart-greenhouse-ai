"""Async CRUD repository for Alert."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert


class AlertRepository:
    """Repository for alert CRUD operations with filtering capabilities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        group_id: uuid.UUID,
        severity: str,
        title: str,
        message: str,
        status: str = "active",
        source: str,
        greenhouse_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        metric: str | None = None,
    ) -> Alert:
        """Create a new alert."""
        alert = Alert(
            group_id=group_id,
            greenhouse_id=greenhouse_id,
            zone_id=zone_id,
            metric=metric,
            severity=severity,
            title=title,
            message=message,
            status=status,
            source=source,
        )
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def get_by_id(self, alert_id: uuid.UUID) -> Alert | None:
        """Fetch a single alert by its UUID."""
        return await self.session.get(Alert, alert_id)

    async def list(self, **filters: Any) -> list[Alert]:
        """List alerts, optionally filtered by status, group, greenhouse, zone, severity, or source."""
        stmt = select(Alert).order_by(Alert.created_at.desc())
        for key, value in filters.items():
            if hasattr(Alert, key) and value is not None:
                stmt = stmt.where(getattr(Alert, key) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(self, status: str) -> list[Alert]:
        """Convenience: list alerts with a given status."""
        return await self.list(status=status)

    async def list_by_group(self, group_id: uuid.UUID, **extra_filters: Any) -> list[Alert]:
        """Convenience: list alerts for a specific group."""
        return await self.list(group_id=group_id, **extra_filters)

    async def list_by_greenhouse(self, greenhouse_id: uuid.UUID, **extra_filters: Any) -> list[Alert]:
        """Convenience: list alerts for a specific greenhouse."""
        return await self.list(greenhouse_id=greenhouse_id, **extra_filters)

    async def list_by_zone(self, zone_id: uuid.UUID, **extra_filters: Any) -> list[Alert]:
        """Convenience: list alerts for a specific zone."""
        return await self.list(zone_id=zone_id, **extra_filters)

    async def update(self, alert_id: uuid.UUID, **kwargs: Any) -> Alert | None:
        """Update fields on an existing alert."""
        alert = await self.session.get(Alert, alert_id)
        if alert is None:
            return None
        for key, value in kwargs.items():
            if hasattr(Alert, key):
                setattr(alert, key, value)
        await self.session.flush()
        return alert

    async def delete(self, alert_id: uuid.UUID) -> bool:
        """Delete an alert by UUID. Returns True if found and deleted."""
        alert = await self.session.get(Alert, alert_id)
        if alert is None:
            return False
        await self.session.delete(alert)
        await self.session.flush()
        return True
