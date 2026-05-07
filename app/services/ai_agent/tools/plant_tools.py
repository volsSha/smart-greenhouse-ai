"""Plant batch and profile read-only tools for the AI agent."""

from __future__ import annotations

import uuid

from pydantic_ai import RunContext

from app.services.ai_agent.tools.deps import ToolDeps


async def get_plant_batches(ctx: RunContext[ToolDeps], group_id: str) -> list[dict]:
    """List all plant batches for a group.

    Walks all greenhouses and zones in the group and collects plant
    batches.
    """
    gid = uuid.UUID(group_id)
    greenhouses = await ctx.deps.greenhouse_repo.list(group_id=gid)
    batches_out: list[dict] = []
    for gh in greenhouses:
        zones = await ctx.deps.zone_repo.list(greenhouse_id=gh.id)
        for z in zones:
            batches = await ctx.deps.plant_batch_repo.list_by_zone(z.id)
            for b in batches:
                batches_out.append({
                    "batch_id": str(b.id),
                    "name": b.name,
                    "species": b.species,
                    "cultivar": b.cultivar,
                    "growth_stage": b.growth_stage,
                    "planted_at": str(b.planted_at) if b.planted_at else None,
                    "greenhouse_id": str(gh.id),
                    "greenhouse_name": gh.name,
                    "zone_id": str(z.id),
                    "zone_name": z.name,
                })
    return batches_out


async def get_plant_profile(ctx: RunContext[ToolDeps], profile_id: str) -> dict:
    """Get a plant profile by ID including all threshold ranges.

    Returns temperature, humidity, soil moisture, CO2, and light
    min/opt/max thresholds.
    """
    pid = uuid.UUID(profile_id)
    profile = await ctx.deps.plant_profile_repo.get_by_id(pid)
    if profile is None:
        return {"error": f"Plant profile {profile_id} not found"}

    return {
        "profile_id": str(profile.id),
        "crop_name": profile.crop_name,
        "growth_stage": profile.growth_stage,
        "temperature": {
            "min": profile.temp_min,
            "optimal": profile.temp_opt,
            "max": profile.temp_max,
        },
        "humidity": {
            "min": profile.humidity_min,
            "optimal": profile.humidity_opt,
            "max": profile.humidity_max,
        },
        "soil_moisture": {
            "min": profile.soil_moisture_min,
            "optimal": profile.soil_moisture_opt,
            "max": profile.soil_moisture_max,
        },
        "co2": {
            "min": profile.co2_min,
            "optimal": profile.co2_opt,
            "max": profile.co2_max,
        },
        "light": {
            "min": profile.light_min,
            "optimal": profile.light_opt,
            "max": profile.light_max,
        },
        "description": profile.description,
    }
