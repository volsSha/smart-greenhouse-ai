"""Alert read-only tools for the AI agent."""

from __future__ import annotations

import uuid

from pydantic_ai import RunContext

from app.services.ai_agent.tools.deps import ToolDeps


async def get_active_alerts(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str | None = None,
    zone_id: str | None = None,
) -> list[dict]:
    """Get active alerts filtered by scope.

    Filters by group_id, and optionally by greenhouse_id and/or zone_id.
    """
    filters: dict = {
        "group_id": uuid.UUID(group_id),
        "status": "active",
    }
    if greenhouse_id is not None:
        filters["greenhouse_id"] = uuid.UUID(greenhouse_id)
    if zone_id is not None:
        filters["zone_id"] = uuid.UUID(zone_id)

    alerts = await ctx.deps.alert_repo.list(**filters)
    return [
        {
            "alert_id": str(a.id),
            "group_id": str(a.group_id),
            "greenhouse_id": str(a.greenhouse_id) if a.greenhouse_id else None,
            "zone_id": str(a.zone_id) if a.zone_id else None,
            "severity": a.severity,
            "title": a.title,
            "message": a.message,
            "metric": a.metric,
            "source": a.source,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]
