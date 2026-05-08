"""REST endpoints for command lifecycle: propose, approve, cancel, recent."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_command_publisher, get_db_session
from app.schemas.commands import CommandPropose, CommandResponse
from app.services.command_publisher import CommandPublisher
from app.services.command_service import CommandError, CommandService

router = APIRouter(prefix="/api/commands", tags=["commands"])


@router.post("/propose", response_model=CommandResponse, status_code=201)
async def propose_command(
    body: CommandPropose,
    session: AsyncSession = Depends(get_db_session),
) -> CommandResponse:
    """Propose a new actuator command.

    Runs safety validation. Returns the command with status 'validated'
    if safe, or 'proposed' with validation_errors if unsafe.
    """
    service = CommandService(session)
    try:
        command = await service.propose(body)
        await session.commit()
        return CommandResponse.model_validate(command)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Command scope does not exist. Check group, greenhouse, and zone IDs.",
        ) from exc


@router.post("/{command_id}/approve", response_model=CommandResponse)
async def approve_command(
    command_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    publisher: CommandPublisher = Depends(get_command_publisher),
) -> CommandResponse:
    """Approve, revalidate, and execute a proposed or validated command."""
    service = CommandService(session, publisher=publisher)
    try:
        command = await service.approve(command_id, execute=True)
        await session.commit()
        return CommandResponse.model_validate(command)
    except CommandError as e:
        raise HTTPException(status_code=409, detail=e.message)


@router.post("/{command_id}/cancel", response_model=CommandResponse)
async def cancel_command(
    command_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> CommandResponse:
    """Cancel a command that is in a cancellable state."""
    service = CommandService(session)
    try:
        command = await service.cancel(command_id)
        await session.commit()
        return CommandResponse.model_validate(command)
    except CommandError as e:
        raise HTTPException(status_code=409, detail=e.message)


@router.get("/groups/{group_id}/recent", response_model=list[CommandResponse])
async def list_recent_commands(
    group_id: UUID,
    greenhouse_id: UUID | None = None,
    zone_id: UUID | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session),
) -> list[CommandResponse]:
    """List recent commands for a group, optionally filtered by greenhouse or zone."""
    service = CommandService(session)
    commands = await service.get_recent(
        group_id=group_id,
        greenhouse_id=greenhouse_id,
        zone_id=zone_id,
        limit=limit,
    )
    return [CommandResponse.model_validate(c) for c in commands]
