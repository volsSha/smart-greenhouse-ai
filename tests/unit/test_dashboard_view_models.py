"""Unit tests for dashboard view model transformations.

Tests the pure data transformation functions that convert raw API
responses into card/chart structures. No UI rendering is involved.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.ui.pages.dashboard import (
    alert_identity,
    build_group_data,
    format_datetime_input,
    normalize_alert,
    parse_datetime_input,
    range_query_limit,
    time_range_bounds,
    transform_latest_to_greenhouses,
    transform_latest_to_zones,
)


# ---------------------------------------------------------------------------
# Test data factories
# ---------------------------------------------------------------------------


def _make_reading(
    group_id: str = "group-001",
    greenhouse_id: str = "gh-001",
    zone_id: str = "zone-01",
    sensor_id: str = "temp-01",
    metric: str = "temperature",
    value: float = 22.5,
    timestamp: str = "2025-01-15T12:00:00Z",
    **extra,
) -> dict:
    """Create a raw reading dict matching InfluxDB query result shape."""
    return {
        "group_id": group_id,
        "greenhouse_id": greenhouse_id,
        "zone_id": zone_id,
        "sensor_id": sensor_id,
        "metric": metric,
        "_value": value,
        "quality": "ok",
        "_time": timestamp,
        **extra,
    }


# ---------------------------------------------------------------------------
# time range helpers
# ---------------------------------------------------------------------------


class TestTimeRangeHelpers:
    def test_time_range_bounds_uses_requested_preset(self) -> None:
        now = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)
        start, end = time_range_bounds("30m", now)

        assert end == now
        assert start.isoformat() == "2026-05-20T11:30:00+00:00"

    def test_range_query_limit_scales_for_long_ranges(self) -> None:
        start = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
        end = datetime(2026, 5, 20, 13, 0, tzinfo=timezone.utc)

        assert range_query_limit(start, end) == 10000

    def test_datetime_input_round_trip_uses_utc(self) -> None:
        value = datetime(2026, 5, 20, 12, 30, tzinfo=timezone.utc)

        assert format_datetime_input(value) == "2026-05-20T12:30"
        assert parse_datetime_input("2026-05-20T12:30") == value


# ---------------------------------------------------------------------------
# transform_latest_to_greenhouses
# ---------------------------------------------------------------------------


class TestTransformLatestToGreenhouses:
    """Tests for transform_latest_to_greenhouses."""

    def test_empty_readings_returns_empty_dict(self) -> None:
        result = transform_latest_to_greenhouses([])
        assert result == {}

    def test_single_reading_creates_one_greenhouse(self) -> None:
        readings = [_make_reading()]
        result = transform_latest_to_greenhouses(readings)

        assert "gh-001" in result
        assert result["gh-001"]["greenhouse_id"] == "gh-001"
        assert result["gh-001"]["group_id"] == "group-001"
        assert result["gh-001"]["zone_count"] == 1
        assert "temperature" in result["gh-001"]["metrics"]
        assert result["gh-001"]["metrics"]["temperature"] == 22.5

    def test_multiple_greenhouses_grouped_correctly(self) -> None:
        readings = [
            _make_reading(greenhouse_id="gh-001", metric="temperature", value=22.0),
            _make_reading(greenhouse_id="gh-002", metric="temperature", value=24.0),
            _make_reading(greenhouse_id="gh-001", metric="air_humidity", value=60.0),
        ]
        result = transform_latest_to_greenhouses(readings)

        assert len(result) == 2
        assert result["gh-001"]["metrics"]["temperature"] == 22.0
        assert result["gh-001"]["metrics"]["air_humidity"] == 60.0
        assert result["gh-002"]["metrics"]["temperature"] == 24.0

    def test_zone_count_reflects_distinct_zones(self) -> None:
        readings = [
            _make_reading(greenhouse_id="gh-001", zone_id="zone-01"),
            _make_reading(greenhouse_id="gh-001", zone_id="zone-02"),
            _make_reading(greenhouse_id="gh-001", zone_id="zone-01", metric="air_humidity"),
        ]
        result = transform_latest_to_greenhouses(readings)

        assert result["gh-001"]["zone_count"] == 2

    def test_first_value_used_when_duplicate_metrics(self) -> None:
        """Readings are sorted desc, so the first value is the latest."""
        readings = [
            _make_reading(metric="temperature", value=25.0, timestamp="2025-01-15T13:00:00Z"),
            _make_reading(metric="temperature", value=20.0, timestamp="2025-01-15T12:00:00Z"),
        ]
        result = transform_latest_to_greenhouses(readings)

        # First reading (higher timestamp) should be kept
        assert result["gh-001"]["metrics"]["temperature"] == 25.0

    def test_multiple_metrics_preserved(self) -> None:
        readings = [
            _make_reading(metric="temperature", value=22.5),
            _make_reading(metric="air_humidity", value=55.0),
            _make_reading(metric="soil_moisture", value=40.0),
            _make_reading(metric="co2", value=450.0),
            _make_reading(metric="light", value=8000.0),
        ]
        result = transform_latest_to_greenhouses(readings)

        metrics = result["gh-001"]["metrics"]
        assert len(metrics) == 5
        assert metrics["temperature"] == 22.5
        assert metrics["soil_moisture"] == 40.0
        assert metrics["light"] == 8000.0


# ---------------------------------------------------------------------------
# transform_latest_to_zones
# ---------------------------------------------------------------------------


class TestTransformLatestToZones:
    """Tests for transform_latest_to_zones."""

    def test_empty_readings_returns_empty_list(self) -> None:
        result = transform_latest_to_zones([], "gh-001")
        assert result == []

    def test_filters_by_greenhouse_id(self) -> None:
        readings = [
            _make_reading(greenhouse_id="gh-001", zone_id="zone-01", metric="temperature"),
            _make_reading(greenhouse_id="gh-002", zone_id="zone-01", metric="temperature"),
        ]
        result = transform_latest_to_zones(readings, "gh-001")

        assert len(result) == 1
        assert result[0]["zone_id"] == "zone-01"

    def test_groups_metrics_by_zone(self) -> None:
        readings = [
            _make_reading(zone_id="zone-01", metric="temperature", value=22.0),
            _make_reading(zone_id="zone-01", metric="air_humidity", value=60.0),
            _make_reading(zone_id="zone-02", metric="temperature", value=24.0),
        ]
        result = transform_latest_to_zones(readings, "gh-001")

        assert len(result) == 2

        zone_01 = next(z for z in result if z["zone_id"] == "zone-01")
        assert zone_01["metrics"]["temperature"] == 22.0
        assert zone_01["metrics"]["air_humidity"] == 60.0

        zone_02 = next(z for z in result if z["zone_id"] == "zone-02")
        assert zone_02["metrics"]["temperature"] == 24.0

    def test_no_matching_greenhouse_returns_empty(self) -> None:
        readings = [_make_reading(greenhouse_id="gh-001")]
        result = transform_latest_to_zones(readings, "gh-999")
        assert result == []


# ---------------------------------------------------------------------------
# alert_identity
# ---------------------------------------------------------------------------


class TestAlertIdentity:
    def test_prefers_persisted_alert_id(self) -> None:
        alert = {
            "id": "alert-001",
            "_time": "2026-05-20T12:00:00Z",
            "greenhouse_id": "gh-001",
            "zone_id": "zone-01",
            "metric": "temperature",
            "_value": 42.0,
            "severity": "critical",
        }

        assert alert_identity(alert) == "alert-001"

    def test_stable_for_same_non_persisted_alert(self) -> None:
        alert = {
            "_time": "2026-05-20T12:00:00Z",
            "greenhouse_id": "gh-001",
            "zone_id": "zone-01",
            "metric": "temperature",
            "_value": 42.0,
            "severity": "critical",
        }

        assert alert_identity(alert) == alert_identity(dict(alert))

    def test_distinguishes_repeated_non_persisted_alert_values_at_different_times(self) -> None:
        first = _make_reading(timestamp="2026-05-20T12:00:00Z", value=42.0)
        second = _make_reading(timestamp="2026-05-20T12:01:00Z", value=42.0)

        assert alert_identity(first) != alert_identity(second)


class TestNormalizeAlert:
    def test_uses_created_at_as_display_timestamp(self) -> None:
        alert = {"id": "alert-001", "created_at": "2026-05-20T12:00:00Z"}

        assert normalize_alert(alert)["timestamp"] == "2026-05-20T12:00:00Z"

    def test_preserves_existing_timestamp(self) -> None:
        alert = {
            "id": "alert-001",
            "created_at": "2026-05-20T12:00:00Z",
            "timestamp": "12:00",
        }

        assert normalize_alert(alert)["timestamp"] == "12:00"


# ---------------------------------------------------------------------------
# build_group_data
# ---------------------------------------------------------------------------


class TestBuildGroupData:
    """Tests for build_group_data."""

    def test_basic_group_data(self) -> None:
        greenhouses = {
            "gh-001": {"greenhouse_id": "gh-001", "metrics": {}},
            "gh-002": {"greenhouse_id": "gh-002", "metrics": {}},
        }
        active_alerts = [{"id": "alert-001", "severity": "warning"}]

        result = build_group_data(greenhouses, active_alerts, "group-001")

        assert result["group_id"] == "group-001"
        assert result["name"] == "group-001"
        assert result["greenhouse_count"] == 2
        assert result["active_alerts"] == 1

    def test_empty_greenhouses_and_alerts(self) -> None:
        result = build_group_data({}, [], "group-001")

        assert result["greenhouse_count"] == 0
        assert result["active_alerts"] == 0

    def test_counts_persisted_alerts_not_raw_anomaly_shape(self) -> None:
        greenhouses = {"gh-001": {"greenhouse_id": "gh-001", "metrics": {}}}
        active_alerts = [
            {"id": "alert-001", "severity": "critical", "title": "Temperature high"},
            {"id": "alert-002", "severity": "warning", "title": "Soil moisture low"},
        ]
        raw_anomalies = [_make_reading(timestamp=f"2026-05-20T12:{minute:02d}:00Z") for minute in range(100)]

        result = build_group_data(greenhouses, active_alerts, "group-001")
        assert result["active_alerts"] == 2
        assert all("title" not in anomaly for anomaly in raw_anomalies)
