"""Command history read-only tools for the AI agent."""

from __future__ import annotations

import uuid

from pydantic_ai import RunContext

from app.services.ai_agent.tools.deps import ToolDeps


async def get_recent_commands(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str | None = None,
    zone_id: str | None = None,
) -> list[dict]:
    """Get recent commands for a group, optionally filtered by scope.

    Returns the most recent commands with their status, actuator, action,
    and reason.
    """
    gid = uuid.UUID(group_id)
    ghid = uuid.UUID(greenhouse_id) if greenhouse_id else None
    zid = uuid.UUID(zone_id) if zone_id else None

    commands = await ctx.deps.command_repo.get_recent(
        group_id=gid,
        greenhouse_id=ghid,
        zone_id=zid,
    )
    return [
        {
            "command_id": str(c.id),
            "group_id": str(c.group_id),
            "greenhouse_id": str(c.greenhouse_id),
            "zone_id": str(c.zone_id),
            "actuator": c.actuator_name,
            "action": c.action,
            "value": c.value,
            "unit": c.unit,
            "duration_seconds": c.duration_seconds,
            "status": c.status,
            "source": c.source,
            "reason": c.reason,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in commands
    ]
