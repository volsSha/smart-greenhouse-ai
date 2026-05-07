"""Group-level read-only tools for the AI agent."""

from __future__ import annotations

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
    return overview
