"""Rule-based control proposals for scoped telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.schemas.commands import CommandPropose


@dataclass(frozen=True)
class ZoneTelemetrySnapshot:
    group_id: UUID
    greenhouse_id: UUID
    zone_id: UUID
    readings: dict[str, float]
    thresholds: dict[str, tuple[float | None, float | None]]


@dataclass(frozen=True)
class ControlProposal:
    command: CommandPropose
    severity: str
    message: str


def evaluate_zone_rules(snapshot: ZoneTelemetrySnapshot) -> list[ControlProposal]:
    """Return command proposals for clear threshold breaches."""
    proposals: list[ControlProposal] = []
    soil_moisture = snapshot.readings.get("soil_moisture")
    soil_min, _soil_max = snapshot.thresholds.get("soil_moisture", (None, None))
    if soil_moisture is not None and soil_min is not None and soil_moisture < soil_min:
        deficit = soil_min - soil_moisture
        duration = 60 if deficit > 10 else 30
        proposals.append(
            ControlProposal(
                command=CommandPropose(
                    group_id=snapshot.group_id,
                    greenhouse_id=snapshot.greenhouse_id,
                    zone_id=snapshot.zone_id,
                    actuator="pump",
                    action="on",
                    duration_seconds=duration,
                    reason=f"Soil moisture {soil_moisture} is below minimum {soil_min}.",
                    source="control_engine",
                ),
                severity="critical" if deficit > 10 else "warning",
                message="Low soil moisture detected",
            )
        )

    temperature = snapshot.readings.get("temperature")
    _temp_min, temp_max = snapshot.thresholds.get("temperature", (None, None))
    if temperature is not None and temp_max is not None and temperature > temp_max:
        proposals.append(
            ControlProposal(
                command=CommandPropose(
                    group_id=snapshot.group_id,
                    greenhouse_id=snapshot.greenhouse_id,
                    zone_id=snapshot.zone_id,
                    actuator="fan",
                    action="set_power",
                    value=75.0,
                    reason=f"Temperature {temperature} exceeds maximum {temp_max}.",
                    source="control_engine",
                ),
                severity="warning",
                message="High temperature detected",
            )
        )
    return proposals
