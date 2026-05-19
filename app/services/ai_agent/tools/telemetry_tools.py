"""Telemetry read-only tools for the AI agent."""

from __future__ import annotations

from uuid import UUID

from pydantic_ai import RunContext

from app.services.ai_agent.tools.deps import ToolDeps


async def get_today_group_summary(ctx: RunContext[ToolDeps], group_id: str) -> list[dict]:
    """Get today's aggregated group telemetry summary.

    Returns min/max/latest per metric for the entire group.
    """
    return ctx.deps.telemetry_repo.get_group_summary(await _resolve_group_id(ctx, group_id))


async def get_today_greenhouse_summary(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str,
) -> list[dict]:
    """Get today's greenhouse telemetry summary.

    Returns min/max/latest per metric for a specific greenhouse.
    """
    resolved_group_id, resolved_greenhouse_id, _ = await _resolve_scope_ids(
        ctx, group_id, greenhouse_id=greenhouse_id,
    )
    return ctx.deps.telemetry_repo.get_greenhouse_summary(
        resolved_group_id, resolved_greenhouse_id,
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
    resolved_group_id, resolved_greenhouse_id, resolved_zone_id = await _resolve_scope_ids(
        ctx, group_id, greenhouse_id=greenhouse_id, zone_id=zone_id,
    )
    return ctx.deps.telemetry_repo.get_zone_summary(
        resolved_group_id, resolved_greenhouse_id, resolved_zone_id,
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
    resolved_group_id, resolved_greenhouse_id, resolved_zone_id = await _resolve_scope_ids(
        ctx, group_id, greenhouse_id=greenhouse_id, zone_id=zone_id,
    )
    return ctx.deps.telemetry_repo.get_latest(
        resolved_group_id,
        greenhouse_id=resolved_greenhouse_id,
        zone_id=resolved_zone_id,
    )


async def _resolve_group_id(ctx: RunContext[ToolDeps], group_id: str) -> str:
    group_uuid = _uuid_or_none(group_id)
    if group_uuid is not None:
        return str(group_uuid)
    groups = await ctx.deps.group_repo.list(name=str(group_id))
    group = groups[0] if isinstance(groups, list) and groups else None
    return str(group.id) if group is not None else str(group_id)


async def _resolve_scope_ids(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str | None = None,
    zone_id: str | None = None,
) -> tuple[str, str | None, str | None]:
    group_uuid = _uuid_or_none(group_id)
    greenhouse_uuid = _uuid_or_none(greenhouse_id) if greenhouse_id else None
    zone_uuid = _uuid_or_none(zone_id) if zone_id else None
    if group_uuid is not None and (greenhouse_id is None or greenhouse_uuid is not None) and (zone_id is None or zone_uuid is not None):
        return str(group_uuid), str(greenhouse_uuid) if greenhouse_uuid else None, str(zone_uuid) if zone_uuid else None

    if group_uuid is not None:
        group = await ctx.deps.group_repo.get_by_id(group_uuid)
    else:
        groups = await ctx.deps.group_repo.list(name=str(group_id))
        group = groups[0] if isinstance(groups, list) and groups else None
    resolved_group_id = str(group.id) if group is not None else str(group_uuid or group_id)

    greenhouse = None
    if greenhouse_id:
        if greenhouse_uuid is not None:
            greenhouse = await ctx.deps.greenhouse_repo.get_by_id(greenhouse_uuid)
            if group is not None and greenhouse is not None and greenhouse.group_id != group.id:
                greenhouse = None
        elif group is not None:
            greenhouses = await ctx.deps.greenhouse_repo.list(group_id=group.id, name=str(greenhouse_id))
            greenhouse = greenhouses[0] if isinstance(greenhouses, list) and greenhouses else None
    resolved_greenhouse_id = str(greenhouse.id) if greenhouse is not None else str(greenhouse_uuid or greenhouse_id) if greenhouse_id else None

    zone = None
    if zone_id:
        if zone_uuid is not None:
            zone = await ctx.deps.zone_repo.get_by_id(zone_uuid)
            if greenhouse is not None and zone is not None and zone.greenhouse_id != greenhouse.id:
                zone = None
        elif greenhouse is not None:
            zones = await ctx.deps.zone_repo.list(greenhouse_id=greenhouse.id, name=str(zone_id))
            zone = zones[0] if isinstance(zones, list) and zones else None
    resolved_zone_id = str(zone.id) if zone is not None else str(zone_uuid or zone_id) if zone_id else None

    return resolved_group_id, resolved_greenhouse_id, resolved_zone_id


def _uuid_or_none(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None
