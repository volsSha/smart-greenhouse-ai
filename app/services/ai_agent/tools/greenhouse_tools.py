"""Greenhouse-level read-only tools for the AI agent."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic_ai import RunContext

from app.services.ai_agent.tools.deps import ToolDeps


async def get_greenhouse_list(ctx: RunContext[ToolDeps], group_id: str) -> list[dict]:
    """List all greenhouses in a group.

    Returns a list of dicts with id, name, location, and zone_count.
    """
    try:
        gid = uuid.UUID(group_id)
    except ValueError:
        return _greenhouse_list_from_telemetry(ctx.deps.telemetry_repo.get_latest(group_id))

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
    if result:
        return result
    return _greenhouse_list_from_telemetry(ctx.deps.telemetry_repo.get_latest(group_id))


async def get_greenhouse_state(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str,
) -> dict:
    """Get the detailed state of a single greenhouse.

    Includes zone summaries, latest readings, and active alerts.
    """
    try:
        gh_id = uuid.UUID(greenhouse_id)
    except ValueError:
        return _greenhouse_state_from_telemetry(
            greenhouse_id,
            ctx.deps.telemetry_repo.get_latest(group_id, greenhouse_id=greenhouse_id),
        )

    gh = await ctx.deps.greenhouse_repo.get_by_id(gh_id)
    if gh is None:
        telemetry_state = _greenhouse_state_from_telemetry(
            greenhouse_id,
            ctx.deps.telemetry_repo.get_latest(group_id, greenhouse_id=greenhouse_id),
        )
        if telemetry_state["zones"]:
            return telemetry_state
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
    try:
        gid = uuid.UUID(group_id)
    except ValueError:
        return _compare_greenhouses_from_telemetry(ctx.deps.telemetry_repo.get_latest(group_id))

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
    if result:
        return result
    return _compare_greenhouses_from_telemetry(ctx.deps.telemetry_repo.get_latest(group_id))


def _greenhouse_list_from_telemetry(readings: list[dict[str, Any]]) -> list[dict]:
    greenhouses: dict[str, set[str]] = {}
    for reading in readings:
        greenhouse_id = reading.get("greenhouse_id")
        zone_id = reading.get("zone_id")
        if not greenhouse_id:
            continue
        greenhouses.setdefault(greenhouse_id, set())
        if zone_id:
            greenhouses[greenhouse_id].add(zone_id)

    return [
        {
            "greenhouse_id": greenhouse_id,
            "name": greenhouse_id,
            "location": None,
            "zone_count": len(zones),
            "source": "telemetry",
        }
        for greenhouse_id, zones in sorted(greenhouses.items())
    ]


def _greenhouse_state_from_telemetry(greenhouse_id: str, readings: list[dict[str, Any]]) -> dict:
    zones: dict[str, dict[str, Any]] = {}
    for reading in readings:
        zone_id = reading.get("zone_id")
        metric = reading.get("metric")
        if not zone_id:
            continue
        zone = zones.setdefault(zone_id, {"zone_id": zone_id, "name": zone_id, "latest_metrics": {}})
        if metric:
            zone["latest_metrics"][metric] = reading.get("_value", reading.get("value"))

    return {
        "greenhouse_id": greenhouse_id,
        "name": greenhouse_id,
        "location": None,
        "zones": [zones[zone_id] for zone_id in sorted(zones)],
        "active_alert_count": 0,
        "source": "telemetry",
    }


def _compare_greenhouses_from_telemetry(readings: list[dict[str, Any]]) -> list[dict]:
    summaries = _greenhouse_list_from_telemetry(readings)
    for summary in summaries:
        summary["active_alert_count"] = 0
    return summaries
