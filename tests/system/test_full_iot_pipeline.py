"""System-level IoT pipeline invariants."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.core.mqtt_topics import command_topic, telemetry_topic
from app.schemas.telemetry import TelemetryEnvelope, TelemetryReading
from app.services.telemetry_ingestion import TelemetryIngestion


@pytest.mark.asyncio
async def test_full_iot_pipeline_accepts_scoped_simulator_message() -> None:
    ingestion = TelemetryIngestion()
    topic = telemetry_topic("group-001", "gh-001", "zone-01")
    payload = TelemetryEnvelope(
        message_id="system-telemetry-1",
        reading=TelemetryReading(
            group_id="group-001",
            greenhouse_id="gh-001",
            zone_id="zone-01",
            sensor_id="sensor-temp",
            metric="temperature",
            value=23.5,
            timestamp=datetime.now(timezone.utc),
        ),
    )

    await ingestion.process_message(topic, json.dumps(payload.model_dump(mode="json")).encode())

    assert ingestion.processed_count == 1
    assert ingestion.error_count == 0
    assert command_topic("group-001", "gh-001", "zone-01").endswith("/commands")
