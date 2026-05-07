"""Approval-required AI tools for creating actuator command proposals."""

from __future__ import annotations

from uuid import UUID

from pydantic_ai import RunContext

from app.schemas.commands import CommandPropose
from app.services.ai_agent.tools.deps import ToolDeps
from app.services.command_service import CommandService


async def propose_watering_action(
    ctx: RunContext[ToolDeps],
    group_id: UUID,
    greenhouse_id: UUID,
    zone_id: UUID,
    duration_seconds: int,
    reason: str,
) -> dict[str, object]:
    """Create a pending pump command proposal for user approval."""
    return await _create_proposal(
        ctx,
        CommandPropose(
            group_id=group_id,
            greenhouse_id=greenhouse_id,
            zone_id=zone_id,
            actuator="pump",
            action="on",
            duration_seconds=duration_seconds,
            reason=reason,
            source="ai_agent",
        ),
    )


async def propose_ventilation_action(
    ctx: RunContext[ToolDeps],
    group_id: UUID,
    greenhouse_id: UUID,
    zone_id: UUID,
    value: float,
    reason: str,
) -> dict[str, object]:
    """Create a pending fan power command proposal for user approval."""
    return await _create_proposal(
        ctx,
        CommandPropose(
            group_id=group_id,
            greenhouse_id=greenhouse_id,
            zone_id=zone_id,
            actuator="fan",
            action="set_power",
            value=value,
            reason=reason,
            source="ai_agent",
        ),
    )


async def propose_lighting_action(
    ctx: RunContext[ToolDeps],
    group_id: UUID,
    greenhouse_id: UUID,
    zone_id: UUID,
    action: str,
    reason: str,
) -> dict[str, object]:
    """Create a pending lamp command proposal for user approval."""
    return await _create_proposal(
        ctx,
        CommandPropose(
            group_id=group_id,
            greenhouse_id=greenhouse_id,
            zone_id=zone_id,
            actuator="lamp",
            action=action,
            reason=reason,
            source="ai_agent",
        ),
    )


async def propose_heater_setpoint_action(
    ctx: RunContext[ToolDeps],
    group_id: UUID,
    greenhouse_id: UUID,
    zone_id: UUID,
    value: float,
    reason: str,
) -> dict[str, object]:
    """Create a pending heater power command proposal for user approval."""
    return await _create_proposal(
        ctx,
        CommandPropose(
            group_id=group_id,
            greenhouse_id=greenhouse_id,
            zone_id=zone_id,
            actuator="heater",
            action="set_power",
            value=value,
            reason=reason,
            source="ai_agent",
        ),
    )


async def _create_proposal(ctx: RunContext[ToolDeps], data: CommandPropose) -> dict[str, object]:
    service = CommandService(ctx.deps.command_repo.session)
    command = await service.propose(data)
    result = {
        "command_id": str(command.id),
        "group_id": str(command.group_id),
        "greenhouse_id": str(command.greenhouse_id),
        "zone_id": str(command.zone_id),
        "actuator": command.actuator_name,
        "action": command.action,
        "value": command.value,
        "duration_seconds": command.duration_seconds,
        "reason": command.reason,
        "status": command.status,
        "valid_until": command.valid_until.isoformat() if command.valid_until else None,
        "validation_errors": command.validation_errors,
        "requires_confirmation": True,
    }
    return result
