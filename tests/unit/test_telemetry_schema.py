"""Tests for telemetry Pydantic schemas."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.telemetry import (
    Quality,
    TelemetryEnvelope,
    TelemetryReading,
    TelemetryValidator,
)


NOW = datetime.now(timezone.utc)


class TestTelemetryReading:
    def test_valid_reading(self) -> None:
        r = TelemetryReading(
            group_id="g1", greenhouse_id="gh1", zone_id="z1",
            sensor_id="s1", metric="temperature", value=22.5,
            timestamp=NOW,
        )
        assert r.metric == "temperature"
        assert r.value == 22.5
        assert r.quality == Quality.OK

    def test_reject_unknown_metric(self) -> None:
        with pytest.raises(ValueError, match="Unknown metric"):
            TelemetryReading(
                group_id="g1", greenhouse_id="gh1", zone_id="z1",
                sensor_id="s1", metric="unknown_metric", value=1.0,
                timestamp=NOW,
            )

    def test_reject_nan_value(self) -> None:
        with pytest.raises(ValueError, match="finite number"):
            TelemetryReading(
                group_id="g1", greenhouse_id="gh1", zone_id="z1",
                sensor_id="s1", metric="temperature", value=float("nan"),
                timestamp=NOW,
            )

    def test_reject_inf_value(self) -> None:
        with pytest.raises(ValueError, match="finite number"):
            TelemetryReading(
                group_id="g1", greenhouse_id="gh1", zone_id="z1",
                sensor_id="s1", metric="temperature", value=float("inf"),
                timestamp=NOW,
            )

    def test_all_valid_metrics(self) -> None:
        from app.core.safety_limits import VALID_METRICS
        for metric in VALID_METRICS:
            r = TelemetryReading(
                group_id="g1", greenhouse_id="gh1", zone_id="z1",
                sensor_id="s1", metric=metric, value=1.0, timestamp=NOW,
            )
            assert r.metric == metric


class TestTelemetryEnvelope:
    def test_valid_envelope(self) -> None:
        e = TelemetryEnvelope(
            message_id="msg-1",
            reading=TelemetryReading(
                group_id="g1", greenhouse_id="gh1", zone_id="z1",
                sensor_id="s1", metric="soil_moisture", value=55.0,
                timestamp=NOW,
            ),
        )
        assert e.message_id == "msg-1"
        assert e.reading.metric == "soil_moisture"

    def test_envelope_without_message_id(self) -> None:
        e = TelemetryEnvelope(
            reading=TelemetryReading(
                group_id="g1", greenhouse_id="gh1", zone_id="z1",
                sensor_id="s1", metric="temperature", value=20.0,
                timestamp=NOW,
            ),
        )
        assert e.message_id is None

    def test_envelope_serialization(self) -> None:
        e = TelemetryEnvelope(
            message_id="msg-1",
            reading=TelemetryReading(
                group_id="g1", greenhouse_id="gh1", zone_id="z1",
                sensor_id="s1", metric="co2", value=420.0,
                timestamp=NOW,
            ),
        )
        d = e.model_dump(mode="json")
        assert d["message_id"] == "msg-1"
        assert d["reading"]["metric"] == "co2"


class TestTelemetryValidator:
    def test_accepts_current_timestamp(self) -> None:
        validator = TelemetryValidator(now=NOW)
        validator.validate_timestamp(NOW)

    def test_default_reference_time_is_current_per_validation(self) -> None:
        validator = TelemetryValidator()
        validator.validate_timestamp(datetime.now(timezone.utc))

    def test_rejects_future_timestamp(self) -> None:
        validator = TelemetryValidator(now=NOW)
        with pytest.raises(ValueError, match="outside the acceptance window"):
            validator.validate_timestamp(NOW + timedelta(minutes=10))

    def test_rejects_stale_timestamp(self) -> None:
        validator = TelemetryValidator(now=NOW)
        with pytest.raises(ValueError, match="outside the acceptance window"):
            validator.validate_timestamp(NOW - timedelta(minutes=10))

    def test_accepts_edge_of_window(self) -> None:
        validator = TelemetryValidator(
            now=NOW, window=timedelta(minutes=5)
        )
        validator.validate_timestamp(NOW + timedelta(minutes=4, seconds=59))
