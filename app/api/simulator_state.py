"""Simulator zone-state API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.simulator_zone import ZoneStateRead
from app.services.simulator.zone_state import SimulatedZoneState

router = APIRouter(prefix="/api/simulator", tags=["simulator"])


def _get_sim_state(request: Request) -> SimulatedZoneState | None:
    return getattr(request.app.state, "simulated_zone_state", None)


@router.get("/zones", response_model=list[ZoneStateRead])
async def get_zone_states(request: Request) -> list[ZoneStateRead]:
    """Return all simulated zone states, or an empty list if not running."""
    sim_state = _get_sim_state(request)
    if sim_state is None or not sim_state.is_initialized:
        return []
    zones = await sim_state.all_states()
    return [_zone_to_read(z) for z in zones]


def _zone_to_read(zone) -> ZoneStateRead:
    return ZoneStateRead(
        group_id=zone.group_id,
        greenhouse_id=zone.greenhouse_id,
        zone_id=zone.zone_id,
        temperature=zone.temperature,
        air_humidity=zone.air_humidity,
        soil_moisture=zone.soil_moisture,
        co2=zone.co2,
        light=zone.light,
        actuators=zone.actuator_states(),
        animation_flags=zone.animation_flags(),
    )
