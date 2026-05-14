"""Approval-required AI tools for creating actuator command proposals."""

from __future__ import annotations

from uuid import UUID


from pydantic_ai import RunContext

from app.schemas.commands import CommandPropose
from app.services.ai_agent.tools.deps import ToolDeps
from app.services.command_service import CommandService


async def propose_watering_action(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str,
    zone_id: str,
    duration_seconds: int,
    reason: str,
) -> dict[str, object]:
    """Create a pending pump command proposal for user approval."""
    resolved = await _resolve_scope(ctx, group_id, greenhouse_id, zone_id)
    if isinstance(resolved, dict):
        return resolved
    return await _create_proposal(
        ctx,
        CommandPropose(
            group_id=resolved[0],
            greenhouse_id=resolved[1],
            zone_id=resolved[2],
            actuator="pump",
            action="on",
            duration_seconds=duration_seconds,
            reason=reason,
            source="ai_agent",
        ),
    )


async def propose_ventilation_action(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str,
    zone_id: str,
    value: float,
    reason: str,
) -> dict[str, object]:
    """Create a pending fan power command proposal for user approval."""
    resolved = await _resolve_scope(ctx, group_id, greenhouse_id, zone_id)
    if isinstance(resolved, dict):
        return resolved
    return await _create_proposal(
        ctx,
        CommandPropose(
            group_id=resolved[0],
            greenhouse_id=resolved[1],
            zone_id=resolved[2],
            actuator="fan",
            action="set_power",
            value=value,
            reason=reason,
            source="ai_agent",
        ),
    )


async def propose_lighting_action(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str,
    zone_id: str,
    action: str,
    reason: str,
) -> dict[str, object]:
    """Create a pending lamp command proposal for user approval."""
    resolved = await _resolve_scope(ctx, group_id, greenhouse_id, zone_id)
    if isinstance(resolved, dict):
        return resolved
    return await _create_proposal(
        ctx,
        CommandPropose(
            group_id=resolved[0],
            greenhouse_id=resolved[1],
            zone_id=resolved[2],
            actuator="lamp",
            action=action,
            reason=reason,
            source="ai_agent",
        ),
    )


async def propose_heater_setpoint_action(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str,
    zone_id: str,
    value: float,
    reason: str,
) -> dict[str, object]:
    """Create a pending heater power command proposal for user approval."""
    resolved = await _resolve_scope(ctx, group_id, greenhouse_id, zone_id)
    if isinstance(resolved, dict):
        return resolved
    return await _create_proposal(
        ctx,
        CommandPropose(
            group_id=resolved[0],
            greenhouse_id=resolved[1],
            zone_id=resolved[2],
            actuator="heater",
            action="set_power",
            value=value,
            reason=reason,
            source="ai_agent",
        ),
    )


async def _resolve_scope(
    ctx: RunContext[ToolDeps],
    group_id: str | UUID,
    greenhouse_id: str | UUID,
    zone_id: str | UUID,
) -> tuple[UUID, UUID, UUID] | dict[str, object]:
    if isinstance(group_id, UUID) and isinstance(greenhouse_id, UUID) and isinstance(zone_id, UUID):
        return group_id, greenhouse_id, zone_id

    try:
        return UUID(str(group_id)), UUID(str(greenhouse_id)), UUID(str(zone_id))
    except ValueError:
        pass

    groups = await ctx.deps.group_repo.list(name=group_id)
    group = groups[0] if groups else None
    if group is None:
        return {"error": f"Group {group_id} not found", "requires_confirmation": False}

    greenhouses = await ctx.deps.greenhouse_repo.list(group_id=group.id, name=greenhouse_id)
    greenhouse = greenhouses[0] if greenhouses else None
    if greenhouse is None:
        return {
            "error": f"Greenhouse {greenhouse_id} not found in group {group_id}",
            "requires_confirmation": False,
        }

    zones = await ctx.deps.zone_repo.list(greenhouse_id=greenhouse.id, name=zone_id)
    zone = zones[0] if zones else None
    if zone is None:
        return {
            "error": f"Zone {zone_id} not found in greenhouse {greenhouse_id}",
            "requires_confirmation": False,
        }

    return group.id, greenhouse.id, zone.id


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
