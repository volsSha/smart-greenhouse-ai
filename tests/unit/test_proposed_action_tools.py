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


def _ctx_with_scope(group_id: uuid.UUID, greenhouse_id: uuid.UUID, zone_id: uuid.UUID) -> SimpleNamespace:
    group = SimpleNamespace(id=group_id, name="group-001")
    greenhouse = SimpleNamespace(id=greenhouse_id, name="gh-001", group_id=group_id)
    zone = SimpleNamespace(id=zone_id, name="zone-01", greenhouse_id=greenhouse_id)
    deps = SimpleNamespace(
        command_repo=SimpleNamespace(session=MagicMock()),
        group_repo=SimpleNamespace(list=AsyncMock(return_value=[group])),
        greenhouse_repo=SimpleNamespace(list=AsyncMock(return_value=[greenhouse])),
        zone_repo=SimpleNamespace(list=AsyncMock(return_value=[zone])),
    )
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


@pytest.mark.asyncio
async def test_propose_lighting_action_accepts_display_identifiers() -> None:
    group_id = uuid.uuid4()
    greenhouse_id = uuid.uuid4()
    zone_id = uuid.uuid4()
    command_id = uuid.uuid4()
    fake_command = SimpleNamespace(
        id=command_id,
        group_id=group_id,
        greenhouse_id=greenhouse_id,
        zone_id=zone_id,
        actuator_name="lamp",
        action="on",
        value=None,
        duration_seconds=None,
        reason="low light",
        status="validated",
        valid_until=datetime.now(timezone.utc),
        validation_errors=None,
    )

    from app.services.ai_agent.tools.proposed_action_tools import propose_lighting_action

    with patch(
        "app.services.ai_agent.tools.proposed_action_tools.CommandService"
    ) as Service:
        service = Service.return_value
        service.propose = AsyncMock(return_value=fake_command)
        result = await propose_lighting_action(
            _ctx_with_scope(group_id, greenhouse_id, zone_id),
            "group-001",
            "gh-001",
            "zone-01",
            "on",
            "low light",
        )

    proposal = service.propose.await_args.args[0]
    assert proposal.group_id == group_id
    assert proposal.greenhouse_id == greenhouse_id
    assert proposal.zone_id == zone_id
    assert result["group_id"] == str(group_id)
    assert result["status"] == "validated"
