"""Tests for simulator lifecycle API helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api import simulator
from app.api.simulator import SimulatorStartRequest


@asynccontextmanager
async def _session_factory():
    yield MagicMock()


def _request() -> SimpleNamespace:
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                telemetry_repository=MagicMock(),
                session_factory=_session_factory,
            )
        )
    )


@pytest.mark.asyncio
async def test_start_simulator_rejects_mqtt_control_mode() -> None:
    request = _request()
    simulator._state["running"] = False

    with patch("app.api.simulator.ModelSettingsRepository") as MockRepo:
        repo = MockRepo.return_value
        repo.bootstrap_settings = AsyncMock(return_value=SimpleNamespace(control_mode="mqtt"))

        with pytest.raises(HTTPException) as exc:
            await simulator.start_simulator(request, SimulatorStartRequest())

    assert exc.value.status_code == 409
    assert "MQTT remote devices mode" in exc.value.detail
    assert not simulator._state["running"]


@pytest.mark.asyncio
async def test_start_simulator_allows_simulator_control_mode() -> None:
    request = _request()
    simulator._state["running"] = False

    with (
        patch("app.api.simulator.ModelSettingsRepository") as MockRepo,
        patch("app.api.simulator.provision_simulator_topology", new_callable=AsyncMock) as provision,
        patch("asyncio.create_task") as create_task,
    ):
        repo = MockRepo.return_value
        repo.bootstrap_settings = AsyncMock(return_value=SimpleNamespace(control_mode="simulator"))
        provision.return_value = [
            simulator.ProvisionedZone(
                group_id="group-1",
                greenhouse_id="greenhouse-1",
                zone_id="zone-1",
            )
        ]
        create_task.return_value = MagicMock()

        status = await simulator.start_simulator(request, SimulatorStartRequest())

    assert status.running is True
    provision.assert_awaited_once()
    create_task.assert_called_once()
    create_task.call_args.args[0].close()
    await simulator.stop_simulator_task(request.app.state)
