"""Greenhouse-level read-only tools for the AI agent."""

from __future__ import annotations

import uuid

from pydantic_ai import RunContext

from app.services.ai_agent.tools.deps import ToolDeps


async def get_greenhouse_list(ctx: RunContext[ToolDeps], group_id: str) -> list[dict]:
    """List all greenhouses in a group.

    Returns a list of dicts with id, name, location, and zone_count.
    """
    gid = uuid.UUID(group_id)
    greenhouses = await ctx.deps.greenhouse_repo.list(group_id=gid)
    result: list[dict] = []
    for gh in greenhouses:
        zones = await ctx.deps.zone_repo.list(greenhouse_id=gh.id)
        result.append({
            "greenhouse_id": str(gh.id),
            "name": gh.name,
            "location": gh.location,
            "zone_count": len(zones),
        })
    return result


async def get_greenhouse_state(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str,
) -> dict:
    """Get the detailed state of a single greenhouse.

    Includes zone summaries, latest readings, and active alerts.
    """
    gh_id = uuid.UUID(greenhouse_id)
    gh = await ctx.deps.greenhouse_repo.get_by_id(gh_id)
    if gh is None:
        return {"error": f"Greenhouse {greenhouse_id} not found"}

    zones = await ctx.deps.zone_repo.list(greenhouse_id=gh_id)
    alerts = await ctx.deps.alert_repo.list(
        group_id=uuid.UUID(group_id),
        greenhouse_id=gh_id,
        status="active",
    )

    zone_summaries: list[dict] = []
    for z in zones:
        zone_alerts = [a for a in alerts if a.zone_id == z.id]
        zone_summaries.append({
            "zone_id": str(z.id),
            "name": z.name,
            "active_alert_count": len(zone_alerts),
        })

    return {
        "greenhouse_id": str(gh.id),
        "name": gh.name,
        "location": gh.location,
        "zones": zone_summaries,
        "active_alert_count": len(alerts),
    }


async def compare_greenhouses(ctx: RunContext[ToolDeps], group_id: str) -> list[dict]:
    """Compare greenhouse summaries across a group.

    Returns a list of greenhouse summaries with zone counts and active
    alert counts for side-by-side comparison.
    """
    gid = uuid.UUID(group_id)
    greenhouses = await ctx.deps.greenhouse_repo.list(group_id=gid)
    result: list[dict] = []
    for gh in greenhouses:
        zones = await ctx.deps.zone_repo.list(greenhouse_id=gh.id)
        alerts = await ctx.deps.alert_repo.list(
            group_id=gid,
            greenhouse_id=gh.id,
            status="active",
        )
        result.append({
            "greenhouse_id": str(gh.id),
            "name": gh.name,
            "location": gh.location,
            "zone_count": len(zones),
            "active_alert_count": len(alerts),
        })
    return result
