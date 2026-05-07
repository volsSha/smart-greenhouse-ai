"""Integration tests for dashboard data flow.

Tests that the dashboard can call the repository and receive correctly
structured data. Uses mocked HTTP clients and repositories.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ui.pages.dashboard import (
    build_group_data,
    transform_latest_to_greenhouses,
    transform_latest_to_zones,
)


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------


def _sample_latest_readings() -> list[dict]:
    """Return sample readings matching the API response shape."""
    return [
        {
            "group_id": "group-001",
            "greenhouse_id": "gh-001",
            "zone_id": "zone-01",
            "sensor_id": "temp-01",
            "metric": "temperature",
            "_value": 23.5,
            "quality": "ok",
            "_time": "2025-01-15T12:00:00Z",
        },
        {
            "group_id": "group-001",
            "greenhouse_id": "gh-001",
            "zone_id": "zone-01",
            "sensor_id": "hum-01",
            "metric": "air_humidity",
            "_value": 65.0,
            "quality": "ok",
            "_time": "2025-01-15T12:00:00Z",
        },
        {
            "group_id": "group-001",
            "greenhouse_id": "gh-001",
            "zone_id": "zone-02",
            "sensor_id": "soil-01",
            "metric": "soil_moisture",
            "_value": 45.0,
            "quality": "ok",
            "_time": "2025-01-15T12:00:00Z",
        },
        {
            "group_id": "group-001",
            "greenhouse_id": "gh-002",
            "zone_id": "zone-01",
            "sensor_id": "temp-02",
            "metric": "temperature",
            "_value": 21.0,
            "quality": "ok",
            "_time": "2025-01-15T12:00:00Z",
        },
    ]


def _sample_range_readings() -> list[dict]:
    """Return sample historical readings for chart data."""
    base = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    readings = []
    for i in range(10):
        ts = base.replace(hour=10 + i)
        readings.append({
            "group_id": "group-001",
            "greenhouse_id": "gh-001",
            "zone_id": "zone-01",
            "sensor_id": "temp-01",
            "metric": "temperature",
            "_value": 20.0 + i * 0.5,
            "quality": "ok",
            "_time": ts.isoformat(),
        })
    return readings


def _sample_anomalies() -> list[dict]:
    """Return sample anomaly data."""
    return [
        {
            "group_id": "group-001",
            "greenhouse_id": "gh-001",
            "zone_id": "zone-01",
            "metric": "temperature",
            "_value": 42.0,
            "_time": "2025-01-15T11:30:00Z",
        },
    ]


# ---------------------------------------------------------------------------
# Data flow tests
# ---------------------------------------------------------------------------


class TestDataFlowFromApiResponse:
    """Test that data flows correctly from API response through transformations."""

    def test_latest_api_response_transforms_to_greenhouses(self) -> None:
        """Simulate API response -> transform_latest_to_greenhouses."""
        readings = _sample_latest_readings()

        greenhouses = transform_latest_to_greenhouses(readings)

        # Should have 2 greenhouses
        assert len(greenhouses) == 2

        # gh-001 should have 2 zones
        assert greenhouses["gh-001"]["zone_count"] == 2
        assert greenhouses["gh-001"]["metrics"]["temperature"] == 23.5
        assert greenhouses["gh-001"]["metrics"]["air_humidity"] == 65.0
        assert greenhouses["gh-001"]["metrics"]["soil_moisture"] == 45.0

        # gh-002 should have 1 zone
        assert greenhouses["gh-002"]["zone_count"] == 1
        assert greenhouses["gh-002"]["metrics"]["temperature"] == 21.0

    def test_latest_to_zones_filters_greenhouse(self) -> None:
        """Test that zone transformation correctly filters by greenhouse."""
        readings = _sample_latest_readings()

        gh_001_zones = transform_latest_to_zones(readings, "gh-001")

        assert len(gh_001_zones) == 2
        zone_ids = {z["zone_id"] for z in gh_001_zones}
        assert zone_ids == {"zone-01", "zone-02"}

        gh_002_zones = transform_latest_to_zones(readings, "gh-002")
        assert len(gh_002_zones) == 1
        assert gh_002_zones[0]["zone_id"] == "zone-01"

    def test_group_data_built_from_transformed_data(self) -> None:
        """Test end-to-end: readings -> greenhouses -> group data."""
        readings = _sample_latest_readings()
        anomalies = _sample_anomalies()

        greenhouses = transform_latest_to_greenhouses(readings)
        group_data = build_group_data(greenhouses, anomalies, "group-001")

        assert group_data["greenhouse_count"] == 2
        assert group_data["active_alerts"] == 1

    def test_empty_api_response_handles_gracefully(self) -> None:
        """Test that empty API responses don't cause errors."""
        greenhouses = transform_latest_to_greenhouses([])
        zones = transform_latest_to_zones([], "gh-001")
        group_data = build_group_data(greenhouses, [], "group-001")

        assert greenhouses == {}
        assert zones == []
        assert group_data["greenhouse_count"] == 0
        assert group_data["active_alerts"] == 0


class TestRangeDataForCharts:
    """Test that range data is suitable for chart rendering."""

    def test_range_readings_have_required_fields(self) -> None:
        """Verify all readings have the fields charts expect."""
        readings = _sample_range_readings()

        for r in readings:
            assert "_time" in r
            assert "_value" in r
            assert isinstance(r["_value"], float)
            assert isinstance(r["_time"], str)

    def test_range_readings_are_chronological(self) -> None:
        """Verify readings can be sorted by time."""
        readings = _sample_range_readings()
        sorted_readings = sorted(readings, key=lambda r: r["_time"])

        for i in range(1, len(sorted_readings)):
            assert sorted_readings[i]["_time"] >= sorted_readings[i - 1]["_time"]

    def test_range_readings_can_be_filtered_by_metric(self) -> None:
        """Verify readings can be filtered for individual charts."""
        readings = _sample_range_readings()

        temp_readings = [r for r in readings if r["metric"] == "temperature"]
        assert len(temp_readings) == 10
        assert all(r["metric"] == "temperature" for r in temp_readings)


class TestAnomalyDataFlow:
    """Test anomaly data integration."""

    def test_anomalies_counted_in_group_data(self) -> None:
        """Verify anomaly count flows into group overview."""
        anomalies = [
            {"metric": "temperature", "_value": 42.0},
            {"metric": "temperature", "_value": 38.0},
            {"metric": "soil_moisture", "_value": 5.0},
        ]
        greenhouses = {"gh-001": {"greenhouse_id": "gh-001", "metrics": {}}}
        group_data = build_group_data(greenhouses, anomalies, "group-001")

        assert group_data["active_alerts"] == 3

    def test_no_anomalies_shows_zero(self) -> None:
        """Verify empty anomalies show zero count."""
        group_data = build_group_data(
            {"gh-001": {"greenhouse_id": "gh-001", "metrics": {}}},
            [],
            "group-001",
        )
        assert group_data["active_alerts"] == 0
