"""Integration tests for MQTT ingestion pipeline.

Tests the full flow: MQTT message -> topic parsing -> schema validation
-> ingestion processing, using mocked MQTT transport.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.telemetry import TelemetryEnvelope, TelemetryReading, Quality
from app.services.mqtt_service import MQTTService
from app.services.telemetry_ingestion import TelemetryIngestion


NOW = datetime.now(timezone.utc)


def _make_payload(
    group_id: str = "g1",
    greenhouse_id: str = "gh1",
    zone_id: str = "z1",
    metric: str = "temperature",
    value: float = 22.5,
    message_id: str | None = None,
) -> bytes:
    envelope = TelemetryEnvelope(
        message_id=message_id,
        reading=TelemetryReading(
            group_id=group_id,
            greenhouse_id=greenhouse_id,
            zone_id=zone_id,
            sensor_id="s1",
            metric=metric,
            value=value,
            quality=Quality.OK,
            timestamp=NOW,
        ),
    )
    return json.dumps(envelope.model_dump(mode="json")).encode()


class TestMQTTIngestionFlow:
    """Test the MQTT -> ingestion pipeline integration."""

    @pytest.mark.asyncio
    async def test_message_flows_from_mqtt_to_ingestion(self) -> None:
        """A valid MQTT message is processed by the ingestion pipeline."""
        ingestion = TelemetryIngestion()
        topic = "greenhouse-groups/g1/greenhouses/gh1/zones/z1/telemetry"
        payload = _make_payload(message_id="flow-1")

        await ingestion.process_message(topic, payload)

        assert ingestion.processed_count == 1
        assert ingestion.error_count == 0

    @pytest.mark.asyncio
    async def test_multiple_messages_accumulate(self) -> None:
        """Multiple valid messages all get processed."""
        ingestion = TelemetryIngestion()

        for i in range(5):
            topic = f"greenhouse-groups/g{i}/greenhouses/gh{i}/zones/z1/telemetry"
            payload = _make_payload(
                group_id=f"g{i}",
                greenhouse_id=f"gh{i}",
                message_id=f"msg-{i}",
            )
            await ingestion.process_message(topic, payload)

        assert ingestion.processed_count == 5

    @pytest.mark.asyncio
    async def test_mixed_valid_invalid_messages(self) -> None:
        """Invalid messages don't block valid ones."""
        ingestion = TelemetryIngestion()
        topic = "greenhouse-groups/g1/greenhouses/gh1/zones/z1/telemetry"

        # Valid message
        await ingestion.process_message(topic, _make_payload(message_id="v1"))

        # Invalid: bad JSON
        await ingestion.process_message(topic, b"broken")

        # Invalid: unknown metric
        bad_payload = json.dumps({
            "reading": {
                "group_id": "g1", "greenhouse_id": "gh1", "zone_id": "z1",
                "sensor_id": "s1", "metric": "bad_metric", "value": 1.0,
                "timestamp": NOW.isoformat(),
            }
        }).encode()
        await ingestion.process_message(topic, bad_payload)

        # Valid message
        await ingestion.process_message(topic, _make_payload(message_id="v2"))

        assert ingestion.processed_count == 2
        assert ingestion.error_count == 2

    @pytest.mark.asyncio
    async def test_wildcard_topic_subscription(self) -> None:
        """Verify the all_telemetry_topic wildcard pattern."""
        from app.core.mqtt_topics import all_telemetry_topic

        pattern = all_telemetry_topic()
        assert pattern == "greenhouse-groups/+/greenhouses/+/zones/+/telemetry"

    @pytest.mark.asyncio
    async def test_mqtt_service_topic_matching(self) -> None:
        """Verify MQTTService topic pattern matcher handles wildcards."""
        assert MQTTService._topic_matches(
            "greenhouse-groups/+/#",
            "greenhouse-groups/g1/greenhouses/gh1/zones/z1/telemetry",
        ) is True
        assert MQTTService._topic_matches(
            "greenhouse-groups/g1/#",
            "greenhouse-groups/g1/greenhouses/gh1/zones/z1/telemetry",
        ) is True
        assert MQTTService._topic_matches(
            "greenhouse-groups/+/#",
            "greenhouse-groups/g1/greenhouses/gh1/zones/z1/commands",
        ) is True
        assert MQTTService._topic_matches(
            "greenhouse-groups/g1/greenhouses/gh1/zones/z1/telemetry",
            "greenhouse-groups/g2/greenhouses/gh1/zones/z1/telemetry",
        ) is False
