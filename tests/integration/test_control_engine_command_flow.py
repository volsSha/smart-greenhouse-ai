"""Integration-style tests for control engine command proposal flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.command_service import CommandService
from services.control_engine.rules import ZoneTelemetrySnapshot, evaluate_zone_rules


def _session() -> AsyncSession:
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.get = AsyncMock(return_value=None)
    return session


@pytest.mark.asyncio
async def test_control_engine_creates_command_proposal_without_publish() -> None:
    snapshot = ZoneTelemetrySnapshot(
        group_id=__import__("uuid").uuid4(),
        greenhouse_id=__import__("uuid").uuid4(),
        zone_id=__import__("uuid").uuid4(),
        readings={"soil_moisture": 18.0},
        thresholds={"soil_moisture": (30.0, 70.0)},
    )
    service = CommandService(_session())
    fake_command = MagicMock(status="validated")

    with (
        patch.object(service.repo, "create", new_callable=AsyncMock, return_value=fake_command) as create,
        patch.object(service.repo, "update_status", new_callable=AsyncMock, return_value=fake_command),
    ):
        proposals = evaluate_zone_rules(snapshot)
        command = await service.propose(proposals[0].command, current_readings=snapshot.readings)

    assert command.status == "validated"
    create.assert_awaited_once()
    assert service.publisher is None
    created = create.await_args.kwargs
    assert created["source"] == "control_engine"
    assert created["actuator_name"] == "pump"
