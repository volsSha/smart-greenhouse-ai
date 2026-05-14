"""Zone-level read-only tools for the AI agent."""

from __future__ import annotations

import uuid

from pydantic_ai import RunContext

from app.services.ai_agent.tools.deps import ToolDeps


async def get_zone_state(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str,
    zone_id: str,
) -> dict:
    """Get the detailed state of a single zone.

    Includes zone metadata, active alerts, sensor count, actuator count,
    and plant batch summary.
    """
    resolved = await _resolve_scope(ctx, group_id, greenhouse_id, zone_id)
    if isinstance(resolved, dict):
        return resolved
    gid, ghid, zid = resolved

    zone = await ctx.deps.zone_repo.get_by_id(zid)
    if zone is None:
        return {"error": f"Zone {zone_id} not found"}

    alerts = await ctx.deps.alert_repo.list(
        group_id=gid,
        greenhouse_id=ghid,
        zone_id=zid,
        status="active",
    )
    sensors = await ctx.deps.sensor_repo.list(zone_id=zid)
    actuators = await ctx.deps.actuator_repo.list(zone_id=zid)
    batches = await ctx.deps.plant_batch_repo.list_by_zone(zid)

    batch_summaries: list[dict] = []
    for b in batches:
        batch_summaries.append({
            "batch_id": str(b.id),
            "name": b.name,
            "species": b.species,
            "growth_stage": b.growth_stage,
        })

    return {
        "zone_id": str(zone.id),
        "name": zone.name,
        "description": zone.description,
        "greenhouse_id": greenhouse_id,
        "sensor_count": len(sensors),
        "actuator_count": len(actuators),
        "plant_batches": batch_summaries,
        "active_alerts": [
            {
                "alert_id": str(a.id),
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "metric": a.metric,
            }
            for a in alerts
        ],
    }


async def get_zone_plant_info(
    ctx: RunContext[ToolDeps],
    group_id: str,
    greenhouse_id: str,
    zone_id: str,
) -> dict:
    """Get plant batch details and profile thresholds for a zone.

    Returns plant batch information along with the profile threshold
    ranges for temperature, humidity, soil moisture, CO2, and light.
    """
    resolved = await _resolve_scope(ctx, group_id, greenhouse_id, zone_id)
    if isinstance(resolved, dict):
        return resolved
    _, _, zid = resolved

    zone = await ctx.deps.zone_repo.get_by_id(zid)
    if zone is None:
        return {"error": f"Zone {zone_id} not found"}

    batches = await ctx.deps.plant_batch_repo.list_by_zone(zid)
    if not batches:
        return {
            "zone_id": str(zid),
            "plant_batches": [],
            "profiles": [],
        }

    batch_summaries: list[dict] = []
    profiles: list[dict] = []
    for b in batches:
        batch_summaries.append({
            "batch_id": str(b.id),
            "name": b.name,
            "species": b.species,
            "cultivar": b.cultivar,
            "planted_at": str(b.planted_at) if b.planted_at else None,
            "growth_stage": b.growth_stage,
            "notes": b.notes,
        })

    return {
        "zone_id": str(zid),
        "plant_batches": batch_summaries,
        "profiles": profiles,
    }


async def _resolve_scope(
    ctx: RunContext[ToolDeps],
    group_id: str | uuid.UUID,
    greenhouse_id: str | uuid.UUID,
    zone_id: str | uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID] | dict:
    if isinstance(group_id, uuid.UUID) and isinstance(greenhouse_id, uuid.UUID) and isinstance(zone_id, uuid.UUID):
        return group_id, greenhouse_id, zone_id

    try:
        return uuid.UUID(str(group_id)), uuid.UUID(str(greenhouse_id)), uuid.UUID(str(zone_id))
    except ValueError:
        pass

    groups = await ctx.deps.group_repo.list(name=group_id)
    group = groups[0] if groups else None
    if group is None:
        return {"error": f"Group {group_id} not found"}

    greenhouses = await ctx.deps.greenhouse_repo.list(group_id=group.id, name=greenhouse_id)
    greenhouse = greenhouses[0] if greenhouses else None
    if greenhouse is None:
        return {"error": f"Greenhouse {greenhouse_id} not found in group {group_id}"}

    zones = await ctx.deps.zone_repo.list(greenhouse_id=greenhouse.id, name=zone_id)
    zone = zones[0] if zones else None
    if zone is None:
        return {"error": f"Zone {zone_id} not found in greenhouse {greenhouse_id}"}

    return group.id, greenhouse.id, zone.id
