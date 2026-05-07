"""Tests for baseline control engine rules."""

from __future__ import annotations

import uuid

from services.control_engine.rules import ZoneTelemetrySnapshot, evaluate_zone_rules


def _snapshot(readings: dict[str, float], thresholds: dict[str, tuple[float | None, float | None]]) -> ZoneTelemetrySnapshot:
    return ZoneTelemetrySnapshot(
        group_id=uuid.uuid4(),
        greenhouse_id=uuid.uuid4(),
        zone_id=uuid.uuid4(),
        readings=readings,
        thresholds=thresholds,
    )


def test_low_soil_moisture_creates_pump_proposal() -> None:
    proposals = evaluate_zone_rules(
        _snapshot({"soil_moisture": 18.0}, {"soil_moisture": (30.0, 70.0)})
    )

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.command.actuator == "pump"
    assert proposal.command.action == "on"
    assert proposal.command.source == "control_engine"
    assert proposal.command.duration_seconds == 60


def test_high_temperature_creates_fan_proposal() -> None:
    proposals = evaluate_zone_rules(
        _snapshot({"temperature": 34.0}, {"temperature": (18.0, 30.0)})
    )

    assert len(proposals) == 1
    assert proposals[0].command.actuator == "fan"
    assert proposals[0].command.action == "set_power"
    assert proposals[0].command.value == 75.0


def test_insufficient_telemetry_creates_no_proposal() -> None:
    proposals = evaluate_zone_rules(_snapshot({}, {"soil_moisture": (30.0, 70.0)}))

    assert proposals == []


def test_in_range_readings_create_no_proposal() -> None:
    proposals = evaluate_zone_rules(
        _snapshot(
            {"soil_moisture": 45.0, "temperature": 24.0},
            {"soil_moisture": (30.0, 70.0), "temperature": (18.0, 30.0)},
        )
    )

    assert proposals == []
