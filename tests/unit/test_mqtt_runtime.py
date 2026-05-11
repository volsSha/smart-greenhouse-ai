"""Tests for application MQTT runtime."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.config import MQTTSettings
from app.core.mqtt_topics import all_telemetry_topic
from app.services.mqtt_runtime import MQTTRuntime


class TestMQTTRuntime:
    @pytest.mark.asyncio
    async def test_start_subscribes_and_listens(self) -> None:
        settings = MQTTSettings(host="localhost", port=1883)
        ingestion = SimpleNamespace(
            processed_count=0,
            error_count=0,
            process_message=AsyncMock(),
        )
        mqtt = AsyncMock()
        mqtt.listen = AsyncMock(return_value=None)
        runtime = MQTTRuntime(settings, ingestion, mqtt_service=mqtt)

        await runtime.start()
        await runtime._task

        mqtt.connect.assert_awaited_once()
        mqtt.subscribe.assert_awaited_once()
        assert mqtt.subscribe.call_args.args[0] == all_telemetry_topic()
        mqtt.listen.assert_awaited_once()
        assert runtime.status().subscribed_topic == all_telemetry_topic()

    @pytest.mark.asyncio
    async def test_stop_cancels_running_task_and_disconnects(self) -> None:
        settings = MQTTSettings(host="localhost", port=1883)
        ingestion = SimpleNamespace(processed_count=0, error_count=0)
        mqtt = AsyncMock()
        mqtt.connect = AsyncMock()
        mqtt.subscribe = AsyncMock()

        async def listen_forever() -> None:
            await asyncio.Event().wait()

        mqtt.listen = AsyncMock(side_effect=listen_forever)
        runtime = MQTTRuntime(settings, ingestion, mqtt_service=mqtt)

        await runtime.start()
        await asyncio.sleep(0)
        await runtime.stop()

        assert runtime.status().running is False
        mqtt.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_message_updates_status_and_calls_ingestion(self) -> None:
        settings = MQTTSettings(host="localhost", port=1883)
        ingestion = SimpleNamespace(
            processed_count=0,
            error_count=0,
            process_message=AsyncMock(),
        )
        mqtt = AsyncMock()
        runtime = MQTTRuntime(settings, ingestion, mqtt_service=mqtt)

        await runtime._handle_message("greenhouse-groups/g/greenhouses/gh/zones/z/telemetry", b"{}")

        ingestion.process_message.assert_awaited_once()
        status = runtime.status()
        assert status.last_message_at is not None
        assert status.last_topic == "greenhouse-groups/g/greenhouses/gh/zones/z/telemetry"

    @pytest.mark.asyncio
    async def test_connection_error_sets_reconnecting_status(self) -> None:
        settings = MQTTSettings(host="localhost", port=1883)
        ingestion = SimpleNamespace(processed_count=0, error_count=0)
        mqtt = AsyncMock()
        mqtt.connect = AsyncMock(side_effect=RuntimeError("broker unavailable"))
        runtime = MQTTRuntime(settings, ingestion, mqtt_service=mqtt)

        await runtime.start()
        await runtime._task

        status = runtime.status()
        assert status.connected is False
        assert status.reconnecting is True
        assert status.last_error == "broker unavailable"
