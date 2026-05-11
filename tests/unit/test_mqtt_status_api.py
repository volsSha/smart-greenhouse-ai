"""Tests for MQTT runtime status API."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.mqtt_status import router
from app.services.mqtt_runtime import MQTTRuntimeStatus


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.mark.asyncio
async def test_mqtt_status_returns_runtime_status() -> None:
    app = create_test_app()
    app.state.mqtt_runtime = SimpleNamespace(
        status=lambda: MQTTRuntimeStatus(
            running=True,
            connected=True,
            reconnecting=False,
            subscribed_topic="greenhouse-groups/+/greenhouses/+/zones/+/telemetry",
            broker_host="mosquitto",
            broker_port=1883,
            last_message_at="2026-05-11T18:00:00Z",
            last_topic="greenhouse-groups/g/greenhouses/gh/zones/z/telemetry",
            last_error=None,
            processed_count=3,
            error_count=1,
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/mqtt/status")

    assert response.status_code == 200
    assert response.json() == {
        "running": True,
        "connected": True,
        "reconnecting": False,
        "subscribed_topic": "greenhouse-groups/+/greenhouses/+/zones/+/telemetry",
        "broker_host": "mosquitto",
        "broker_port": 1883,
        "last_message_at": "2026-05-11T18:00:00Z",
        "last_topic": "greenhouse-groups/g/greenhouses/gh/zones/z/telemetry",
        "last_error": None,
        "processed_count": 3,
        "error_count": 1,
    }


@pytest.mark.asyncio
async def test_mqtt_status_reports_missing_runtime() -> None:
    app = create_test_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/mqtt/status")

    assert response.status_code == 200
    body = response.json()
    assert body["running"] is False
    assert body["connected"] is False
    assert body["last_error"] == "MQTT runtime is not initialized"
