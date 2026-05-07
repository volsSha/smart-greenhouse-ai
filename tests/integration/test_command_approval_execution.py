"""Integration-style tests for command approval and MQTT execution."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.command_service import CommandService


def _session(command: SimpleNamespace) -> AsyncSession:
    session = MagicMock(spec=AsyncSession)
    session.get = AsyncMock(return_value=command)
    session.flush = AsyncMock()
    return session


def _command(status: str = "validated", **overrides) -> SimpleNamespace:
    values = {
        "id": uuid.uuid4(),
        "group_id": uuid.uuid4(),
        "greenhouse_id": uuid.uuid4(),
        "zone_id": uuid.uuid4(),
        "actuator_id": None,
        "actuator_name": "pump",
        "action": "on",
        "value": None,
        "unit": None,
        "duration_seconds": 30,
        "source": "manual",
        "reason": "dry soil",
        "validation_errors": None,
        "status": status,
        "valid_until": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_approval_executes_and_publishes_once() -> None:
    command = _command()
    publisher = MagicMock()
    publisher.publish = AsyncMock(return_value={"topic": "commands", "payload": {"ok": True}})
    service = CommandService(_session(command), publisher=publisher)
    approved = _command(status="approved")
    executing = _command(status="executing")
    executed = _command(status="executed")

    with patch.object(
        service.repo,
        "update_status",
        new_callable=AsyncMock,
        side_effect=[approved, executing, executed],
    ) as update_status:
        result = await service.approve(command.id, execute=True)

    assert result.status == "executed"
    publisher.publish.assert_awaited_once()
    assert [call.args[1] for call in update_status.await_args_list] == [
        "approved",
        "executing",
        "executed",
    ]


@pytest.mark.asyncio
async def test_unsafe_approval_rejects_without_publish() -> None:
    command = _command(actuator_name="heater", action="on", duration_seconds=120)
    publisher = MagicMock()
    publisher.publish = AsyncMock()
    service = CommandService(_session(command), publisher=publisher)
    rejected = _command(status="rejected")

    with patch.object(
        service.repo,
        "update_status",
        new_callable=AsyncMock,
        return_value=rejected,
    ):
        result = await service.approve(
            command.id,
            current_readings={"temperature": 35.0},
            execute=True,
        )

    assert result.status == "rejected"
    publisher.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_mqtt_failure_marks_command_failed() -> None:
    command = _command(status="approved")
    publisher = MagicMock()
    publisher.publish = AsyncMock(side_effect=RuntimeError("broker unavailable"))
    service = CommandService(_session(command), publisher=publisher)
    executing = _command(status="executing")
    failed = _command(status="failed", validation_errors={"errors": ["broker unavailable"]})

    with patch.object(
        service.repo,
        "update_status",
        new_callable=AsyncMock,
        side_effect=[executing, failed],
    ):
        result = await service.execute(command.id)

    assert result.status == "failed"
    publisher.publish.assert_awaited_once()
