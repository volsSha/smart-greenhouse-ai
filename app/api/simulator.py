"""Simulator lifecycle endpoints."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.schemas.telemetry import TelemetryReading
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


async def _run_simulator(config: SimulatorStartRequest, telemetry_repository: Any) -> None:
    try:
        while _state["running"]:
            now = datetime.now(timezone.utc)
            published = 0
            for group in range(1, config.groups + 1):
                for greenhouse in range(1, config.greenhouses_per_group + 1):
                    for zone in range(1, config.zones_per_greenhouse + 1):
                        for metric in ("temperature", "air_humidity", "soil_moisture", "co2", "light"):
                            telemetry_repository.write_telemetry(
                                TelemetryReading(
                                    group_id=f"group-{group:03d}",
                                    greenhouse_id=f"gh-{greenhouse:03d}",
                                    zone_id=f"zone-{zone:02d}",
                                    sensor_id=f"{metric}-{zone:02d}",
                                    metric=metric,
                                    value=_metric_value(metric, config.scenario, group, greenhouse, zone),
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
    sim_state.initialize(
        num_groups=body.groups,
        greenhouses_per_group=body.greenhouses_per_group,
        zones_per_greenhouse=body.zones_per_greenhouse,
        scenario=body.scenario,
    )
    request.app.state.simulated_zone_state = sim_state

    _state["task"] = asyncio.create_task(_run_simulator(body, telemetry_repository))
    return _status()


@router.post("/stop", response_model=SimulatorStatus)
async def stop_simulator(request: Request) -> SimulatorStatus:
    _state["running"] = False
    task: asyncio.Task | None = _state.get("task")
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    _state["task"] = None

    sim_state: SimulatedZoneState | None = getattr(request.app.state, "simulated_zone_state", None)
    if sim_state is not None:
        sim_state.reset()
        delattr(request.app.state, "simulated_zone_state")

    return _status()
