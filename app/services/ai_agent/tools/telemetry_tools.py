"""Telemetry read-only tools for the AI agent."""

from __future__ import annotations

from pydantic_ai import RunContext

from app.services.ai_agent.tools.deps import ToolDeps


async def get_today_group_summary(ctx: RunContext[ToolDeps], group_id: str) -> list[dict]:
    """Get today's aggregated group telemetry summary.

    Returns min/max/latest per metric for the entire group.
    """
    return ctx.deps.telemetry_repo.get_group_summary(group_id)


async def get_today_greenhouse_summary(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str,
) -> list[dict]:
    """Get today's greenhouse telemetry summary.

    Returns min/max/latest per metric for a specific greenhouse.
    """
    return ctx.deps.telemetry_repo.get_greenhouse_summary(
        group_id, greenhouse_id,
    )


async def get_today_zone_summary(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str,
    zone_id: str,
) -> list[dict]:
    """Get today's zone telemetry summary.

    Returns min/max/latest per metric for a specific zone.
    """
    return ctx.deps.telemetry_repo.get_zone_summary(
        group_id, greenhouse_id, zone_id,
    )


async def get_latest_readings(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str | None = None,
    zone_id: str | None = None,
) -> list[dict]:
    """Get the latest telemetry readings for a scope.

    Optionally filter by greenhouse_id and/or zone_id.
    """
    return ctx.deps.telemetry_repo.get_latest(
        group_id,
        greenhouse_id=greenhouse_id,
        zone_id=zone_id,
    )
