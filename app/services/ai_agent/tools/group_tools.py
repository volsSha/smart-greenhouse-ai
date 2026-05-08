"""Group-level read-only tools for the AI agent."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from app.services.ai_agent.tools.deps import ToolDeps


async def get_group_overview(ctx: RunContext[ToolDeps]) -> list[dict]:
    """Return an overview of all groups with greenhouse and zone counts.

    Each entry contains group_id, name, location, greenhouse_count, and
    zone_count.
    """
    groups = await ctx.deps.group_repo.list()
    overview: list[dict] = []
    for g in groups:
        greenhouses = await ctx.deps.greenhouse_repo.list(group_id=g.id)
        zone_count = 0
        for gh in greenhouses:
            zones = await ctx.deps.zone_repo.list(greenhouse_id=gh.id)
            zone_count += len(zones)
        overview.append({
            "group_id": str(g.id),
            "name": g.name,
            "location": g.location,
            "greenhouse_count": len(greenhouses),
            "zone_count": zone_count,
        })
    if overview:
        return overview

    latest = ctx.deps.telemetry_repo.get_latest("group-001")
    return _group_overview_from_telemetry(latest)


def _group_overview_from_telemetry(readings: list[dict[str, Any]]) -> list[dict]:
    groups: dict[str, dict[str, set[str]]] = {}
    for reading in readings:
        group_id = reading.get("group_id")
        greenhouse_id = reading.get("greenhouse_id")
        zone_id = reading.get("zone_id")
        if not group_id:
            continue
        groups.setdefault(group_id, {"greenhouses": set(), "zones": set()})
        if greenhouse_id:
            groups[group_id]["greenhouses"].add(greenhouse_id)
        if zone_id:
            groups[group_id]["zones"].add(zone_id)

    return [
        {
            "group_id": group_id,
            "name": group_id,
            "location": None,
            "greenhouse_count": len(data["greenhouses"]),
            "zone_count": len(data["zones"]),
            "source": "telemetry",
        }
        for group_id, data in sorted(groups.items())
    ]
