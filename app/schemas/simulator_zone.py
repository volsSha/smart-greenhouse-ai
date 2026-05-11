"""Pydantic schemas for simulator zone state."""

from __future__ import annotations

from pydantic import BaseModel


class ActuatorStateRead(BaseModel):
    active: bool = False
    value: float = 0.0
    remaining_seconds: float | None = None


class ZoneStateRead(BaseModel):
    group_id: str
    greenhouse_id: str
    zone_id: str
    temperature: float
    air_humidity: float
    soil_moisture: float
    co2: float
    light: float
    actuators: dict[str, ActuatorStateRead]
    animation_flags: dict[str, bool]
