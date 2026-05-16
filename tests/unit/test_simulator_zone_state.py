"""Tests for SimulatedZoneState service."""

from __future__ import annotations

import pytest

from app.api import simulator
from app.api.simulator import SimulatorStartRequest
from app.services.simulator.zone_state import (
    SimulatedZoneState,
    simulator_greenhouse_id,
    simulator_group_id,
    simulator_zone_id,
)

ZONE_KEY = (simulator_group_id(1), simulator_greenhouse_id(1), simulator_zone_id(1))


@pytest.fixture
def state() -> SimulatedZoneState:
    s = SimulatedZoneState()
    s.initialize(num_groups=1, greenhouses_per_group=1, zones_per_greenhouse=2, scenario="normal")
    return s


class TestInitialize:
    def test_creates_zones(self, state: SimulatedZoneState) -> None:
        assert state.is_initialized
        assert len(state.all_zone_refs()) == 2

    def test_exposes_zone_refs_for_telemetry_generation(self, state: SimulatedZoneState) -> None:
        assert ZONE_KEY in state.all_zone_refs()

    def test_reset_clears_state(self, state: SimulatedZoneState) -> None:
        state.reset()
        assert not state.is_initialized
        assert state.all_zone_refs() == []


class TestApplyCommand:
    @pytest.mark.asyncio
    async def test_watering_increases_soil_moisture(self, state: SimulatedZoneState) -> None:
        key = ZONE_KEY
        zone = await state.get_state(*key)
        before = zone.soil_moisture

        await state.apply_command({
            "group_id": key[0],
            "greenhouse_id": key[1],
            "zone_id": key[2],
            "actuator_name": "pump",
            "action": "on",
            "value": 50.0,
            "duration_seconds": 30,
            "source": "ai_agent",
        })

        effect = await state.telemetry_value(*key, "soil_moisture")
        assert effect > before

    @pytest.mark.asyncio
    async def test_turn_off_resets_actuator(self, state: SimulatedZoneState) -> None:
        key = ZONE_KEY
        await state.apply_command({
            "group_id": key[0], "greenhouse_id": key[1], "zone_id": key[2],
            "actuator_name": "pump", "action": "on", "value": 50.0,
            "duration_seconds": 60, "source": "ai_agent",
        })
        await state.apply_command({
            "group_id": key[0], "greenhouse_id": key[1], "zone_id": key[2],
            "actuator_name": "pump", "action": "off", "source": "ai_agent",
        })
        zone = await state.get_state(*key)
        assert not zone.pump.active
        assert zone.pump.value == 0.0

    @pytest.mark.asyncio
    async def test_heater_raises_temperature(self, state: SimulatedZoneState) -> None:
        key = ZONE_KEY
        await state.apply_command({
            "group_id": key[0], "greenhouse_id": key[1], "zone_id": key[2],
            "actuator_name": "heater", "action": "on", "value": 50.0,
            "duration_seconds": 30, "source": "ai_agent",
        })
        effect = await state.telemetry_value(*key, "temperature")
        zone = await state.get_state(*key)
        assert effect > zone.temperature

    @pytest.mark.asyncio
    async def test_fan_lowers_temperature(self, state: SimulatedZoneState) -> None:
        key = ZONE_KEY
        await state.apply_command({
            "group_id": key[0], "greenhouse_id": key[1], "zone_id": key[2],
            "actuator_name": "fan", "action": "set_power", "value": 80.0,
            "duration_seconds": 30, "source": "ai_agent",
        })
        base = (await state.get_state(*key)).temperature
        effect = await state.telemetry_value(*key, "temperature")
        assert effect < base

    @pytest.mark.asyncio
    async def test_lamp_increases_light(self, state: SimulatedZoneState) -> None:
        key = ZONE_KEY
        await state.apply_command({
            "group_id": key[0], "greenhouse_id": key[1], "zone_id": key[2],
            "actuator_name": "lamp", "action": "on", "value": 100.0,
            "duration_seconds": 60, "source": "ai_agent",
        })
        base = (await state.get_state(*key)).light
        effect = await state.telemetry_value(*key, "light")
        assert effect > base

    @pytest.mark.asyncio
    async def test_unknown_zone_is_noop(self, state: SimulatedZoneState) -> None:
        await state.apply_command({
            "group_id": "nonexistent", "greenhouse_id": "gh-999", "zone_id": "zone-99",
            "actuator_name": "pump", "action": "on", "source": "ai_agent",
        })
        assert len(state._zones) == 2  # unchanged

    @pytest.mark.asyncio
    async def test_unknown_actuator_is_noop(self, state: SimulatedZoneState) -> None:
        key = ZONE_KEY
        await state.apply_command({
            "group_id": key[0], "greenhouse_id": key[1], "zone_id": key[2],
            "actuator_name": "flux_capacitor", "action": "on", "source": "ai_agent",
        })
        zone = await state.get_state(*key)
        assert zone is not None


class TestTelemetryValue:
    @pytest.mark.asyncio
    async def test_no_actuator_returns_baseline(self, state: SimulatedZoneState) -> None:
        val = await state.telemetry_value(*ZONE_KEY, "temperature")
        assert val > 0

    @pytest.mark.asyncio
    async def test_unknown_zone_returns_zero(self, state: SimulatedZoneState) -> None:
        val = await state.telemetry_value("x", "y", "z", "temperature")
        assert val == 0.0

    @pytest.mark.asyncio
    async def test_expired_duration_returns_baseline(self, state: SimulatedZoneState) -> None:
        """Short-duration commands expire and stop affecting telemetry."""
        key = ZONE_KEY
        zone = await state.get_state(*key)
        before_light = zone.light

        await state.apply_command({
            "group_id": key[0], "greenhouse_id": key[1], "zone_id": key[2],
            "actuator_name": "lamp", "action": "on", "value": 100.0,
            "duration_seconds": 0, "source": "ai_agent",
        })
        # 0-second duration should expire immediately on tick
        import time
        time.sleep(0.01)  # allow tick to process
        effect = await state.telemetry_value(*key, "light")
        assert effect == before_light


class TestAnimationFlags:
    @pytest.mark.asyncio
    async def test_active_actuators_have_animation_flag(self, state: SimulatedZoneState) -> None:
        key = ZONE_KEY
        await state.apply_command({
            "group_id": key[0], "greenhouse_id": key[1], "zone_id": key[2],
            "actuator_name": "fan", "action": "set_power", "value": 80.0,
            "duration_seconds": 30, "source": "ai_agent",
        })
        zone = await state.get_state(*key)
        flags = zone.animation_flags()
        assert flags["fan"] is True
        assert flags["pump"] is False


class TestSimulatorTelemetryLoop:
    @pytest.mark.asyncio
    async def test_loop_writes_actuator_adjusted_values(self, state: SimulatedZoneState) -> None:
        class TelemetryRepository:
            def __init__(self) -> None:
                self.rows = []

            def write_telemetry(self, reading) -> None:
                self.rows.append(reading)
                if len(self.rows) >= 5:
                    simulator._state["running"] = False

        await state.apply_command({
            "group_id": ZONE_KEY[0],
            "greenhouse_id": ZONE_KEY[1],
            "zone_id": ZONE_KEY[2],
            "actuator_name": "pump",
            "action": "on",
            "value": 50.0,
            "duration_seconds": 30,
            "source": "manual",
        })
        repository = TelemetryRepository()
        simulator._state["running"] = True

        await simulator._run_simulator(
            SimulatorStartRequest(groups=1, greenhouses_per_group=1, zones_per_greenhouse=1, interval_seconds=1),
            repository,
            state,
        )

        soil = next(row for row in repository.rows if row.metric == "soil_moisture")
        assert soil.zone_id == ZONE_KEY[2]
        assert soil.sensor_id == f"{ZONE_KEY[2]}:soil_moisture"
        assert soil.value == await state.telemetry_value(*ZONE_KEY, "soil_moisture")
