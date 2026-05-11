"""Tests for MQTT service publish behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import MQTTSettings
from app.services.mqtt_service import MQTTService


class TestMQTTServicePublish:
    @pytest.mark.asyncio
    async def test_publish_raises_when_disconnected(self) -> None:
        service = MQTTService(MQTTSettings())

        with pytest.raises(RuntimeError, match="not connected"):
            await service.publish("greenhouse-groups/g/greenhouses/gh/zones/z/commands", "{}")

    @pytest.mark.asyncio
    async def test_publish_reraises_client_errors(self) -> None:
        service = MQTTService(MQTTSettings())
        client = AsyncMock()
        client.publish = AsyncMock(side_effect=RuntimeError("broker rejected publish"))
        service._client = client
        service._running = True

        with pytest.raises(RuntimeError, match="broker rejected publish"):
            await service.publish("greenhouse-groups/g/greenhouses/gh/zones/z/commands", "{}")
