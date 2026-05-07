"""System-level action approval flow invariant."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.command_service import CommandService


@pytest.mark.asyncio
async def test_action_approval_publishes_exactly_once_after_validation() -> None:
    command = SimpleNamespace(
        id=uuid.uuid4(),
        group_id=uuid.uuid4(),
        greenhouse_id=uuid.uuid4(),
        zone_id=uuid.uuid4(),
        actuator_id=None,
        actuator_name="pump",
        action="on",
        value=None,
        unit=None,
        duration_seconds=30,
        source="ai_agent",
        reason="dry soil",
        validation_errors=None,
        status="validated",
        valid_until=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session = MagicMock(spec=AsyncSession)
    session.get = AsyncMock(return_value=command)
    publisher = MagicMock()
    publisher.publish = AsyncMock(return_value={"topic": "commands", "payload": {}})
    service = CommandService(session, publisher=publisher)

    with patch.object(
        service.repo,
        "update_status",
        new_callable=AsyncMock,
        side_effect=[
            SimpleNamespace(**{**command.__dict__, "status": "approved"}),
            SimpleNamespace(**{**command.__dict__, "status": "executing"}),
            SimpleNamespace(**{**command.__dict__, "status": "executed"}),
        ],
    ):
        result = await service.approve(command.id, execute=True)

    assert result.status == "executed"
    publisher.publish.assert_awaited_once()
