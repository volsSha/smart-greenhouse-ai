"""Unit tests for the TelemetryRepository.

Tests query building and write format by mocking the InfluxDB client.
No real InfluxDB connection is required.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock


from app.repositories.telemetry_repository import TelemetryRepository
from app.schemas.telemetry import Quality, TelemetryReading


def _make_reading(
    group_id: str = "group-001",
    greenhouse_id: str = "gh-001",
    zone_id: str = "zone-01",
    sensor_id: str = "temp-01",
    metric: str = "temperature",
    value: float = 22.5,
    quality: Quality = Quality.OK,
    timestamp: datetime | None = None,
) -> TelemetryReading:
    return TelemetryReading(
        group_id=group_id,
        greenhouse_id=greenhouse_id,
        zone_id=zone_id,
        sensor_id=sensor_id,
        metric=metric,
        value=value,
        quality=quality,
        timestamp=timestamp or datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


class TestWriteTelemetry:
    """Tests for write_telemetry method."""

    def test_write_point_called_with_correct_args(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        repo = TelemetryRepository(mock_client)

        reading = _make_reading()
        repo.write_telemetry(reading)

        mock_client.write_point.assert_called_once()
        kwargs = mock_client.write_point.call_args[1]

        assert kwargs["measurement"] == "microclimate"
        tags = kwargs["tags"]
        assert tags["group_id"] == "group-001"
        assert tags["greenhouse_id"] == "gh-001"
        assert tags["zone_id"] == "zone-01"
        assert tags["sensor_id"] == "temp-01"
        assert tags["metric"] == "temperature"

        fields = kwargs["fields"]
        assert fields["value"] == 22.5
        assert fields["quality"] == "ok"

    def test_write_with_warn_quality(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        repo = TelemetryRepository(mock_client)

        reading = _make_reading(quality=Quality.WARN)
        repo.write_telemetry(reading)

        fields = mock_client.write_point.call_args[1]["fields"]
        assert fields["quality"] == "warn"


class TestGetLatest:
    """Tests for get_latest query building."""

    def test_latest_query_includes_group_filter(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        mock_client.query_data.return_value = []
        repo = TelemetryRepository(mock_client)

        repo.get_latest("group-001")

        call_args = mock_client.query_data.call_args[0][0]
        assert 'r.group_id == "group-001"' in call_args
        assert "last()" in call_args

    def test_latest_query_with_greenhouse_filter(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        mock_client.query_data.return_value = []
        repo = TelemetryRepository(mock_client)

        repo.get_latest("group-001", greenhouse_id="gh-002")

        call_args = mock_client.query_data.call_args[0][0]
        assert 'r.greenhouse_id == "gh-002"' in call_args

    def test_latest_query_with_zone_and_metric_filters(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        mock_client.query_data.return_value = []
        repo = TelemetryRepository(mock_client)

        repo.get_latest("group-001", zone_id="zone-03", metric="temperature")

        call_args = mock_client.query_data.call_args[0][0]
        assert 'r.zone_id == "zone-03"' in call_args
        assert 'r.metric == "temperature"' in call_args


class TestGetRange:
    """Tests for get_range query building."""

    def test_range_query_includes_time_bounds(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        mock_client.query_data.return_value = []
        repo = TelemetryRepository(mock_client)

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        repo.get_range("group-001", start=start, end=end)

        call_args = mock_client.query_data.call_args[0][0]
        assert "2025-01-01T00:00:00Z" in call_args
        assert "2025-01-02T00:00:00Z" in call_args

    def test_range_query_with_all_filters(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        mock_client.query_data.return_value = []
        repo = TelemetryRepository(mock_client)

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        repo.get_range(
            "group-001",
            start=start,
            end=end,
            greenhouse_id="gh-001",
            zone_id="zone-01",
            metric="soil_moisture",
        )

        call_args = mock_client.query_data.call_args[0][0]
        assert 'r.greenhouse_id == "gh-001"' in call_args
        assert 'r.zone_id == "zone-01"' in call_args
        assert 'r.metric == "soil_moisture"' in call_args


class TestGetGroupSummary:
    """Tests for get_group_summary query building."""

    def test_summary_query_uses_today_default(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        mock_client.query_data.return_value = []
        repo = TelemetryRepository(mock_client)

        repo.get_group_summary("group-001")

        # Should call query_data at least once (min query)
        assert mock_client.query_data.call_count >= 1

    def test_summary_query_with_custom_range(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        mock_client.query_data.return_value = []
        repo = TelemetryRepository(mock_client)

        start = datetime(2025, 3, 1, tzinfo=timezone.utc)
        end = datetime(2025, 3, 15, tzinfo=timezone.utc)
        repo.get_group_summary("group-001", date_range=(start, end))

        call_args = mock_client.query_data.call_args[0][0]
        assert "2025-03-01" in call_args
        assert "2025-03-15" in call_args


class TestGetGreenhouseSummary:
    """Tests for get_greenhouse_summary query building."""

    def test_greenhouse_summary_includes_greenhouse_filter(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        mock_client.query_data.return_value = []
        repo = TelemetryRepository(mock_client)

        repo.get_greenhouse_summary("group-001", "gh-002")

        call_args = mock_client.query_data.call_args[0][0]
        assert 'r.greenhouse_id == "gh-002"' in call_args


class TestGetZoneSummary:
    """Tests for get_zone_summary query building."""

    def test_zone_summary_includes_zone_filter(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        mock_client.query_data.return_value = []
        repo = TelemetryRepository(mock_client)

        repo.get_zone_summary("group-001", "gh-001", "zone-02")

        call_args = mock_client.query_data.call_args[0][0]
        assert 'r.zone_id == "zone-02"' in call_args


class TestGetAnomalies:
    """Tests for anomaly detection query building."""

    def test_anomaly_query_includes_group_filter(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        mock_client.query_data.return_value = []
        repo = TelemetryRepository(mock_client)

        repo.get_anomalies("group-001")

        call_args = mock_client.query_data.call_args[0][0]
        assert 'r.group_id == "group-001"' in call_args


class TestCompareGreenhouses:
    """Tests for compare_greenhouses query building."""

    def test_compare_query_groups_by_greenhouse(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket = "microclimate"
        mock_client.query_data.return_value = []
        repo = TelemetryRepository(mock_client)

        repo.compare_greenhouses("group-001")

        call_args = mock_client.query_data.call_args[0][0]
        assert '["greenhouse_id", "metric"]' in call_args
        assert 'r.group_id == "group-001"' in call_args


class TestMergeSummaries:
    """Tests for the internal _merge_summaries helper."""

    def test_merge_min_max(self) -> None:
        min_rows = [
            {"metric": "temperature", "_value": 15.0},
            {"metric": "air_humidity", "_value": 40.0},
        ]
        max_rows = [
            {"metric": "temperature", "_value": 30.0},
            {"metric": "air_humidity", "_value": 80.0},
        ]

        result = TelemetryRepository._merge_summaries(min_rows, max_rows)

        metrics = {r["metric"]: r for r in result}
        assert metrics["temperature"]["min"] == 15.0
        assert metrics["temperature"]["max"] == 30.0
        assert metrics["air_humidity"]["min"] == 40.0
        assert metrics["air_humidity"]["max"] == 80.0

    def test_merge_with_last(self) -> None:
        min_rows = [{"metric": "temperature", "_value": 15.0}]
        max_rows = [{"metric": "temperature", "_value": 30.0}]
        last_rows = [{"metric": "temperature", "_value": 22.0}]

        result = TelemetryRepository._merge_summaries(
            min_rows, max_rows, last_rows
        )

        assert len(result) == 1
        assert result[0]["latest"] == 22.0

    def test_merge_empty_results(self) -> None:
        result = TelemetryRepository._merge_summaries([], [])
        assert result == []


class TestResolveDateRange:
    """Tests for date range resolution."""

    def test_custom_range(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        s, e = TelemetryRepository._resolve_date_range((start, end))
        assert "2025-01-01" in s
        assert "2025-01-31" in e

    def test_default_range_is_today(self) -> None:
        s, e = TelemetryRepository._resolve_date_range(None)
        # Should contain today's date
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert today in s


class TestFormatDatetime:
    """Tests for datetime formatting."""

    def test_format_utc_datetime(self) -> None:
        dt = datetime(2025, 6, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = TelemetryRepository._format_datetime(dt)
        assert result == "2025-06-15T10:30:45Z"
