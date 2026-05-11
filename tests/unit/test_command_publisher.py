"""Tests for MQTT command publishing."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.config import MQTTSettings
from app.services.command_publisher import CommandPublisher


class FakePublishClient:
    def __init__(self) -> None:
        self.connected = False
        self.disconnected = False
        self.published: list[tuple[str, str, int]] = []

    async def connect(self) -> None:
        self.connected = True

    async def publish(self, topic: str, payload: bytes | str, qos: int = 0) -> None:
        self.published.append((topic, payload.decode() if isinstance(payload, bytes) else payload, qos))

    async def disconnect(self) -> None:
        self.disconnected = True


@pytest.mark.asyncio
async def test_publish_uses_scoped_command_topic_and_payload() -> None:
    client = FakePublishClient()
    publisher = CommandPublisher(MQTTSettings(), client=client)
    command = SimpleNamespace(
        id=uuid.uuid4(),
        group_id=uuid.uuid4(),
        greenhouse_id=uuid.uuid4(),
        zone_id=uuid.uuid4(),
        actuator_name="pump",
        action="on",
        value=None,
        duration_seconds=30,
        source="manual",
        reason="dry soil",
        created_at=datetime.now(timezone.utc),
    )

    result = await publisher.publish(command)

    assert client.connected is True
    assert client.disconnected is True
    assert len(client.published) == 1
    topic, payload, qos = client.published[0]
    assert topic == result["topic"]
    assert topic.endswith(f"/zones/{command.zone_id}/commands")
    assert qos == 1
    data = json.loads(payload)
    assert data == {
        "command_id": str(command.id),
        "group_id": str(command.group_id),
        "greenhouse_id": str(command.greenhouse_id),
        "zone_id": str(command.zone_id),
        "actuator": "pump",
        "action": "on",
        "value": None,
        "duration_seconds": 30,
        "source": "manual",
        "reason": "dry soil",
    }
    assert '"value":null' in payload
    assert result["payload"] == data
