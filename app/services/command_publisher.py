"""MQTT publisher for approved actuator commands."""

from __future__ import annotations

import json
from typing import Protocol

from app.config import MQTTSettings
from app.core.mqtt_topics import command_topic
from app.models.command import CommandLog
from app.services.mqtt_service import MQTTService


class PublishClient(Protocol):
    async def connect(self) -> None: ...
    async def publish(self, topic: str, payload: bytes | str, qos: int = 0) -> None: ...
    async def disconnect(self) -> None: ...


class CommandPublisher:
    """Publishes command log entries to scoped MQTT command topics."""

    def __init__(self, settings: MQTTSettings, client: PublishClient | None = None) -> None:
        self.settings = settings
        self.client = client or MQTTService(settings)

    async def publish(self, command: CommandLog) -> dict[str, object]:
        topic = command_topic(
            str(command.group_id),
            str(command.greenhouse_id),
            str(command.zone_id),
        )
        payload = {
            "command_id": str(command.id),
            "group_id": str(command.group_id),
            "greenhouse_id": str(command.greenhouse_id),
            "zone_id": str(command.zone_id),
            "actuator": command.actuator_name,
            "action": command.action,
            "value": command.value,
            "duration_seconds": command.duration_seconds,
            "source": command.source,
            "reason": command.reason,
        }
        await self.client.connect()
        try:
            await self.client.publish(topic, json.dumps(payload, separators=(",", ":")), qos=1)
        finally:
            await self.client.disconnect()
        return {"topic": topic, "payload": payload}
