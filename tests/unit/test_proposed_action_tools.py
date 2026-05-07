"""Tests for approval-required proposed action AI tools."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_agent.tools.proposed_action_tools import propose_watering_action


def _ctx() -> SimpleNamespace:
    command_repo = SimpleNamespace(session=MagicMock())
    deps = SimpleNamespace(command_repo=command_repo)
    return SimpleNamespace(deps=deps)


@pytest.mark.asyncio
async def test_propose_watering_action_creates_pending_command_record() -> None:
    command_id = uuid.uuid4()
    fake_command = SimpleNamespace(
        id=command_id,
        group_id=uuid.uuid4(),
        greenhouse_id=uuid.uuid4(),
        zone_id=uuid.uuid4(),
        actuator_name="pump",
        action="on",
        value=None,
        duration_seconds=45,
        reason="soil is dry",
        status="validated",
        valid_until=datetime.now(timezone.utc),
        validation_errors=None,
    )

    with patch(
        "app.services.ai_agent.tools.proposed_action_tools.CommandService"
    ) as Service:
        service = Service.return_value
        service.propose = AsyncMock(return_value=fake_command)
        result = await propose_watering_action(
            _ctx(),
            fake_command.group_id,
            fake_command.greenhouse_id,
            fake_command.zone_id,
            45,
            "soil is dry",
        )

    service.propose.assert_awaited_once()
    proposal = service.propose.await_args.args[0]
    assert proposal.source == "ai_agent"
    assert proposal.actuator == "pump"
    assert result["command_id"] == str(command_id)
    assert result["requires_confirmation"] is True
    assert result["status"] == "validated"
