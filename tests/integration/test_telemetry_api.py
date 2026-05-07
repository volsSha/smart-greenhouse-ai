"""Integration tests for the Telemetry REST API endpoints.

Tests endpoint shapes and response formats using a mocked repository.
No real InfluxDB connection is required.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def mock_repo():
    """Provide a mocked TelemetryRepository on app state."""
    repo = MagicMock()
    repo.get_latest.return_value = [
        {
            "group_id": "group-001",
            "greenhouse_id": "gh-001",
            "zone_id": "zone-01",
            "sensor_id": "temp-01",
            "metric": "temperature",
            "_value": 22.5,
            "quality": "ok",
            "_time": "2025-01-15T12:00:00Z",
        }
    ]
    repo.get_group_summary.return_value = [
        {"metric": "temperature", "min": 18.0, "max": 28.0},
    ]
    repo.get_greenhouse_summary.return_value = [
        {"metric": "temperature", "min": 18.0, "max": 26.0},
    ]
    repo.get_zone_summary.return_value = [
        {"metric": "temperature", "min": 19.0, "max": 25.0},
    ]
    repo.get_range.return_value = [
        {
            "group_id": "group-001",
            "metric": "temperature",
            "_value": 22.0,
            "_time": "2025-01-15T10:00:00Z",
        },
    ]
    repo.get_anomalies.return_value = []
    repo.compare_greenhouses.return_value = [
        {
            "greenhouse_id": "gh-001",
            "metric": "temperature",
            "_value": 22.0,
        },
        {
            "greenhouse_id": "gh-002",
            "metric": "temperature",
            "_value": 24.0,
        },
    ]

    app.state.telemetry_repository = repo
    yield repo


class TestLatestEndpoint:
    """Tests for GET /api/groups/{group_id}/telemetry/latest."""

    def test_latest_returns_readings_list(self, mock_repo) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/groups/group-001/telemetry/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert "readings" in data
        assert "total" in data
        assert data["total"] == 1

    def test_latest_calls_repo_with_filters(self, mock_repo) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        client.get(
            "/api/groups/group-001/telemetry/latest"
            "?greenhouse_id=gh-001&zone_id=zone-01&metric=temperature"
        )
        mock_repo.get_latest.assert_called_once_with(
            group_id="group-001",
            greenhouse_id="gh-001",
            zone_id="zone-01",
            metric="temperature",
        )


class TestGroupSummaryEndpoint:
    """Tests for GET /api/groups/{group_id}/telemetry/summary/today."""

    def test_group_summary_returns_summaries(self, mock_repo) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/groups/group-001/telemetry/summary/today")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == "group-001"
        assert "summaries" in data
        assert len(data["summaries"]) == 1


class TestGreenhouseSummaryEndpoint:
    """Tests for GET /api/groups/{group_id}/greenhouses/{gh_id}/telemetry/summary/today."""

    def test_greenhouse_summary_returns_correct_shape(self, mock_repo) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/groups/group-001/greenhouses/gh-001/telemetry/summary/today"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == "group-001"
        assert data["greenhouse_id"] == "gh-001"
        assert "summaries" in data


class TestZoneSummaryEndpoint:
    """Tests for GET /api/groups/{group_id}/greenhouses/{gh_id}/zones/{zone_id}/telemetry/summary/today."""

    def test_zone_summary_returns_correct_shape(self, mock_repo) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/groups/group-001/greenhouses/gh-001/zones/zone-01/telemetry/summary/today"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == "group-001"
        assert data["greenhouse_id"] == "gh-001"
        assert data["zone_id"] == "zone-01"
        assert "summaries" in data


class TestRangeEndpoint:
    """Tests for GET /api/groups/{group_id}/telemetry/range."""

    def test_range_returns_readings_with_range_info(self, mock_repo) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        start = "2025-01-15T00:00:00Z"
        end = "2025-01-15T23:59:59Z"
        resp = client.get(
            f"/api/groups/group-001/telemetry/range?start={start}&end={end}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "readings" in data
        assert "total" in data
        assert "range" in data
        # FastAPI serializes with +00:00 instead of Z, so normalize
        assert "2025-01-15T00:00:00" in data["range"]["start"]
        assert "2025-01-15T23:59:59" in data["range"]["end"]

    def test_range_passes_filters_to_repo(self, mock_repo) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        start = "2025-01-01T00:00:00Z"
        end = "2025-01-02T00:00:00Z"
        client.get(
            f"/api/groups/group-001/telemetry/range"
            f"?start={start}&end={end}"
            f"&greenhouse_id=gh-001&zone_id=zone-01&metric=temperature&limit=500"
        )
        mock_repo.get_range.assert_called_once()
        call_kwargs = mock_repo.get_range.call_args[1]
        assert call_kwargs["greenhouse_id"] == "gh-001"
        assert call_kwargs["zone_id"] == "zone-01"
        assert call_kwargs["metric"] == "temperature"
        assert call_kwargs["limit"] == 500

    def test_range_missing_params_returns_422(self, mock_repo) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        # Missing 'end' parameter
        resp = client.get(
            "/api/groups/group-001/telemetry/range?start=2025-01-01T00:00:00Z"
        )
        assert resp.status_code == 422


class TestAnomaliesEndpoint:
    """Tests for GET /api/groups/{group_id}/telemetry/anomalies."""

    def test_anomalies_returns_empty_list(self, mock_repo) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/groups/group-001/telemetry/anomalies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == "group-001"
        assert data["anomalies"] == []
        assert data["total"] == 0

    def test_anomalies_calls_repo_with_group_id(self, mock_repo) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        client.get("/api/groups/group-001/telemetry/anomalies")
        mock_repo.get_anomalies.assert_called_once_with(
            group_id="group-001"
        )


class TestCompareGreenhousesEndpoint:
    """Tests for GET /api/groups/{group_id}/compare-greenhouses."""

    def test_compare_returns_comparison_data(self, mock_repo) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/groups/group-001/compare-greenhouses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == "group-001"
        assert "comparison" in data
        assert len(data["comparison"]) == 2
