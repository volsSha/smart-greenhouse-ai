"""Tests for the ModeRouter service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.command import CommandLog
from app.services.simulator.mode_router import ModeRouter
from app.services.simulator.zone_state import SimulatedZoneState


@pytest.fixture
def sim_state() -> SimulatedZoneState:
    s = SimulatedZoneState()
    s.initialize(num_groups=1, greenhouses_per_group=1, zones_per_greenhouse=2, scenario="normal")
    return s


@pytest.fixture
def session_mock():
    """Return an AsyncSession mock that resolves UUID→name lookups."""
    session = AsyncMock()

    async def get(model, pk):
        if model.__name__ == "GreenhouseGroup":
            m = MagicMock()
            m.name = "group-001"
            return m
        if model.__name__ == "Greenhouse":
            m = MagicMock()
            m.name = "gh-001"
            return m
        if model.__name__ == "GreenhouseZone":
            m = MagicMock()
            m.name = "zone-01"
            return m
        return None

    session.get = get
    return session


def _make_command(mode: str = "simulator", **kwargs) -> CommandLog:
    return MagicMock(
        spec=CommandLog,
        mode=mode,
        group_id="00000000-0000-0000-0000-000000000001",
        greenhouse_id="00000000-0000-0000-0000-000000000002",
        zone_id="00000000-0000-0000-0000-000000000003",
        actuator_name="pump",
        action="on",
        value=50.0,
        duration_seconds=30,
        source="ai_agent",
        **kwargs,
    )


class TestModeRouter:
    async def test_simulator_mode_applies_to_zone_state(
        self, sim_state: SimulatedZoneState, session_mock
    ) -> None:
        router = ModeRouter(sim_state)
        command = _make_command(mode="simulator")

        result = await router.route(command, session_mock)

        assert result == {"mode": "simulator", "applied": True}
        zone = await sim_state.get_state("group-001", "gh-001", "zone-01")
        assert zone is not None
        assert zone.pump.active
        assert zone.pump.value == 50.0

    async def test_mqtt_mode_returns_needs_publish(
        self, sim_state: SimulatedZoneState, session_mock
    ) -> None:
        router = ModeRouter(sim_state)
        command = _make_command(mode="mqtt")

        result = await router.route(command, session_mock)

        assert result == {"mode": "mqtt", "needs_publish": True}

    async def test_simulator_mode_without_state_raises_error(self, session_mock) -> None:
        router = ModeRouter(sim_state=None)
        command = _make_command(mode="simulator")

        with pytest.raises(Exception, match="Simulator is not running"):
            await router.route(command, session_mock)

    async def test_simulator_mode_with_uninitialized_state_raises_error(self, session_mock) -> None:
        state = SimulatedZoneState()
        router = ModeRouter(state)
        command = _make_command(mode="simulator")

        with pytest.raises(Exception, match="Simulator is not running"):
            await router.route(command, session_mock)
