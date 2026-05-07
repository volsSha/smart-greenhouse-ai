"""Tests for telemetry ingestion pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.telemetry import TelemetryEnvelope, TelemetryReading, Quality
from app.services.telemetry_ingestion import TelemetryIngestion


NOW = datetime.now(timezone.utc)


def _make_envelope(
    group_id: str = "g1",
    greenhouse_id: str = "gh1",
    zone_id: str = "z1",
    sensor_id: str = "s1",
    metric: str = "temperature",
    value: float = 22.5,
    message_id: str | None = None,
    timestamp: datetime | None = None,
    quality: str = "ok",
) -> bytes:
    reading = TelemetryReading(
        group_id=group_id,
        greenhouse_id=greenhouse_id,
        zone_id=zone_id,
        sensor_id=sensor_id,
        metric=metric,
        value=value,
        quality=quality,
        timestamp=timestamp or NOW,
    )
    envelope = TelemetryEnvelope(
        message_id=message_id,
        reading=reading,
    )
    return json.dumps(envelope.model_dump(mode="json")).encode()


class TestTelemetryIngestion:
    @pytest.fixture
    def ingestion(self) -> TelemetryIngestion:
        return TelemetryIngestion(acceptance_window=timedelta(minutes=5))

    @pytest.mark.asyncio
    async def test_valid_message_is_processed(self, ingestion: TelemetryIngestion) -> None:
        topic = "greenhouse-groups/g1/greenhouses/gh1/zones/z1/telemetry"
        payload = _make_envelope()
        await ingestion.process_message(topic, payload)
        assert ingestion.processed_count == 1
        assert ingestion.error_count == 0

    @pytest.mark.asyncio
    async def test_non_telemetry_topic_is_ignored(self, ingestion: TelemetryIngestion) -> None:
        topic = "greenhouse-groups/g1/greenhouses/gh1/zones/z1/commands"
        payload = _make_envelope()
        await ingestion.process_message(topic, payload)
        assert ingestion.processed_count == 0

    @pytest.mark.asyncio
    async def test_invalid_json_is_rejected(self, ingestion: TelemetryIngestion) -> None:
        topic = "greenhouse-groups/g1/greenhouses/gh1/zones/z1/telemetry"
        await ingestion.process_message(topic, b"not json")
        assert ingestion.error_count == 1
        assert ingestion.processed_count == 0

    @pytest.mark.asyncio
    async def test_unknown_metric_is_rejected(self, ingestion: TelemetryIngestion) -> None:
        topic = "greenhouse-groups/g1/greenhouses/gh1/zones/z1/telemetry"
        data = {
            "reading": {
                "group_id": "g1", "greenhouse_id": "gh1", "zone_id": "z1",
                "sensor_id": "s1", "metric": "unknown", "value": 1.0,
                "timestamp": NOW.isoformat(),
            }
        }
        await ingestion.process_message(topic, json.dumps(data).encode())
        assert ingestion.error_count == 1

    @pytest.mark.asyncio
    async def test_topic_payload_mismatch_is_rejected(self, ingestion: TelemetryIngestion) -> None:
        topic = "greenhouse-groups/g1/greenhouses/gh1/zones/z1/telemetry"
        payload = _make_envelope(group_id="OTHER")
        await ingestion.process_message(topic, payload)
        assert ingestion.error_count == 1
        assert ingestion.processed_count == 0

    @pytest.mark.asyncio
    async def test_duplicate_message_id_is_skipped(self, ingestion: TelemetryIngestion) -> None:
        topic = "greenhouse-groups/g1/greenhouses/gh1/zones/z1/telemetry"
        payload = _make_envelope(message_id="dup-1")
        await ingestion.process_message(topic, payload)
        await ingestion.process_message(topic, payload)
        assert ingestion.processed_count == 1

    @pytest.mark.asyncio
    async def test_stale_timestamp_is_rejected(self, ingestion: TelemetryIngestion) -> None:
        topic = "greenhouse-groups/g1/greenhouses/gh1/zones/z1/telemetry"
        old_ts = NOW - timedelta(minutes=10)
        payload = _make_envelope(timestamp=old_ts)
        await ingestion.process_message(topic, payload)
        assert ingestion.error_count == 1

    def test_is_valid_metric(self) -> None:
        assert TelemetryIngestion.is_valid_metric("temperature") is True
        assert TelemetryIngestion.is_valid_metric("air_humidity") is True
        assert TelemetryIngestion.is_valid_metric("not_real") is False

    @pytest.mark.asyncio
    async def test_never_crashes_on_bad_input(self, ingestion: TelemetryIngestion) -> None:
        """Absolute safety net: any exception is caught internally."""
        await ingestion.process_message("", b"")
        assert ingestion.error_count >= 0  # didn't raise
