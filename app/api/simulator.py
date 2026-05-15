"""Simulator lifecycle endpoints."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import get_settings
from app.repositories.model_settings_repository import ModelSettingsRepository
from app.schemas.telemetry import TelemetryReading
from app.services.simulator.provisioning import ProvisionedZone, provision_simulator_topology
from app.services.simulator.zone_state import SimulatedZoneState

router = APIRouter(prefix="/api/simulator", tags=["simulator"])


class SimulatorStartRequest(BaseModel):
    scenario: str = "normal"
    groups: int = Field(default=1, ge=1, le=10)
    greenhouses_per_group: int = Field(default=3, ge=1, le=20)
    zones_per_greenhouse: int = Field(default=4, ge=1, le=20)
    interval_seconds: int = Field(default=5, ge=1, le=300)


class SimulatorStatus(BaseModel):
    running: bool
    scenario: str
    messages_published: int
    last_publish: str | None
    last_error: str | None = None


_state: dict[str, Any] = {
    "running": False,
    "scenario": "normal",
    "messages_published": 0,
    "last_publish": None,
    "last_error": None,
    "task": None,
}


def _status() -> SimulatorStatus:
    return SimulatorStatus(
        running=bool(_state["running"]),
        scenario=str(_state["scenario"]),
        messages_published=int(_state["messages_published"]),
        last_publish=_state["last_publish"],
        last_error=_state["last_error"],
    )


def _metric_value(metric: str, scenario: str, group: int, greenhouse: int, zone: int) -> float:
    base_values = {
        "temperature": 24.0,
        "air_humidity": 60.0,
        "soil_moisture": 55.0,
        "co2": 850.0,
        "light": 500.0,
    }
    scenario_offsets = {
        "dry_soil": {"soil_moisture": -40.0},
        "overheating": {"temperature": 16.0},
        "low_light": {"light": -420.0},
        "sensor_fault": {"temperature": 25.0, "air_humidity": -45.0},
    }
    return base_values[metric] + scenario_offsets.get(scenario, {}).get(metric, 0.0) + group + greenhouse + zone


async def _run_simulator(
    config: SimulatorStartRequest,
    telemetry_repository: Any,
    sim_state: SimulatedZoneState,
    zones: list[ProvisionedZone] | None = None,
) -> None:
    try:
        while _state["running"]:
            now = datetime.now(timezone.utc)
            published = 0
            active_zones = zones or [
                ProvisionedZone(group_id=group_id, greenhouse_id=greenhouse_id, zone_id=zone_id)
                for group_id, greenhouse_id, zone_id in sim_state._zones
            ]
            for index, zone in enumerate(active_zones, start=1):
                for metric in ("temperature", "air_humidity", "soil_moisture", "co2", "light"):
                    value = _metric_value(metric, config.scenario, 0, 0, index)
                    if sim_state.is_initialized:
                        value = await sim_state.telemetry_value(zone.group_id, zone.greenhouse_id, zone.zone_id, metric)
                    telemetry_repository.write_telemetry(
                        TelemetryReading(
                            group_id=zone.group_id,
                            greenhouse_id=zone.greenhouse_id,
                            zone_id=zone.zone_id,
                            sensor_id=f"{metric}-{index:02d}",
                            metric=metric,
                            value=value,
                            timestamp=now,
                        )
                    )
                    published += 1
            _state["messages_published"] += published
            _state["last_publish"] = now.isoformat()
            await asyncio.sleep(config.interval_seconds)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _state["last_error"] = str(exc)
        _state["running"] = False


@router.get("/status", response_model=SimulatorStatus)
async def simulator_status() -> SimulatorStatus:
    return _status()


@router.post("/start", response_model=SimulatorStatus)
async def start_simulator(request: Request, body: SimulatorStartRequest) -> SimulatorStatus:
    if _state["running"]:
        raise HTTPException(status_code=409, detail="Simulator is already running")

    telemetry_repository = request.app.state.telemetry_repository
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=503, detail="Database session factory is not available")

    async with session_factory() as session:
        settings_repo = ModelSettingsRepository(session)
        app_settings = get_settings()
        settings = await settings_repo.bootstrap_settings(
            embedding_model=app_settings.openrouter.embedding_model,
            embedding_dimension=app_settings.openrouter.embedding_dimension,
        )
        if settings.control_mode == "mqtt":
            raise HTTPException(
                status_code=409,
                detail="Simulator cannot run while MQTT remote devices mode is selected. Switch control mode to Internal simulator in Settings first.",
            )

        provisioned_zones = await provision_simulator_topology(
            session,
            groups=body.groups,
            greenhouses_per_group=body.greenhouses_per_group,
            zones_per_greenhouse=body.zones_per_greenhouse,
        )

    _state.update(
        {
            "running": True,
            "scenario": body.scenario,
            "messages_published": 0,
            "last_publish": None,
            "last_error": None,
        }
    )
    sim_state = SimulatedZoneState()
    sim_state.initialize_from_zones(
        [(zone.group_id, zone.greenhouse_id, zone.zone_id) for zone in provisioned_zones],
        scenario=body.scenario,
    )
    request.app.state.simulated_zone_state = sim_state

    _state["task"] = asyncio.create_task(_run_simulator(body, telemetry_repository, sim_state, provisioned_zones))
    return _status()


async def stop_simulator_task(app_state: Any | None = None) -> None:
    _state["running"] = False
    task: asyncio.Task | None = _state.get("task")
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    _state["task"] = None

    if app_state is None:
        return

    sim_state: SimulatedZoneState | None = getattr(app_state, "simulated_zone_state", None)
    if sim_state is not None:
        sim_state.reset()
        delattr(app_state, "simulated_zone_state")


@router.post("/stop", response_model=SimulatorStatus)
async def stop_simulator(request: Request) -> SimulatorStatus:
    await stop_simulator_task(request.app.state)
    return _status()
