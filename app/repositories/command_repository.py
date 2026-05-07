"""Async CRUD repository for CommandLog."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.command import CommandLog


class CommandRepository:
    """Repository for command log CRUD operations with filtering."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        group_id: uuid.UUID,
        greenhouse_id: uuid.UUID,
        zone_id: uuid.UUID,
        actuator_name: str,
        action: str,
        value: float | None = None,
        unit: str | None = None,
        duration_seconds: int | None = None,
        source: str = "manual",
        reason: str | None = None,
        status: str = "proposed",
        validation_errors: dict | None = None,
        valid_until: datetime | None = None,
        actuator_id: uuid.UUID | None = None,
    ) -> CommandLog:
        """Create a new command log entry."""
        command = CommandLog(
            group_id=group_id,
            greenhouse_id=greenhouse_id,
            zone_id=zone_id,
            actuator_id=actuator_id,
            actuator_name=actuator_name,
            action=action,
            value=value,
            unit=unit,
            duration_seconds=duration_seconds,
            source=source,
            reason=reason,
            validation_errors=validation_errors,
            status=status,
            valid_until=valid_until,
        )
        self.session.add(command)
        await self.session.flush()
        return command

    async def get_by_id(self, command_id: uuid.UUID) -> CommandLog | None:
        """Fetch a single command by its UUID."""
        return await self.session.get(CommandLog, command_id)

    async def list(
        self,
        *,
        group_id: uuid.UUID | None = None,
        greenhouse_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        status: str | None = None,
        source: str | None = None,
    ) -> list[CommandLog]:
        """List commands, optionally filtered."""
        stmt = select(CommandLog).order_by(CommandLog.created_at.desc())

        if group_id is not None:
            stmt = stmt.where(CommandLog.group_id == group_id)
        if greenhouse_id is not None:
            stmt = stmt.where(CommandLog.greenhouse_id == greenhouse_id)
        if zone_id is not None:
            stmt = stmt.where(CommandLog.zone_id == zone_id)
        if status is not None:
            stmt = stmt.where(CommandLog.status == status)
        if source is not None:
            stmt = stmt.where(CommandLog.source == source)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        command_id: uuid.UUID,
        status: str,
        validation_errors: dict | None = None,
    ) -> CommandLog | None:
        """Update the status of a command (and optionally its validation errors)."""
        command = await self.session.get(CommandLog, command_id)
        if command is None:
            return None
        command.status = status
        if validation_errors is not None:
            command.validation_errors = validation_errors
        await self.session.flush()
        return command

    async def get_recent(
        self,
        group_id: uuid.UUID,
        greenhouse_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[CommandLog]:
        """Fetch the most recent commands for a group, optionally filtered."""
        stmt = (
            select(CommandLog)
            .where(CommandLog.group_id == group_id)
            .order_by(CommandLog.created_at.desc())
            .limit(limit)
        )
        if greenhouse_id is not None:
            stmt = stmt.where(CommandLog.greenhouse_id == greenhouse_id)
        if zone_id is not None:
            stmt = stmt.where(CommandLog.zone_id == zone_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
