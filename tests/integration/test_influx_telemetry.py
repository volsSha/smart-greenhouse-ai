"""Integration tests for InfluxDB client and telemetry persistence.

Tests InfluxDB client initialization, point construction, and query
formatting. Uses a mocked InfluxDB connection so no live server is needed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.influx_client import InfluxClient
from app.schemas.telemetry import Quality, TelemetryReading
from app.repositories.telemetry_repository import TelemetryRepository


class TestInfluxClientInit:
    """Tests for InfluxClient initialization."""

    @patch("app.services.influx_client.InfluxDBClient")
    def test_client_created_with_correct_params(self, mock_cls) -> None:
        InfluxClient(
            url="http://localhost:8086",
            token="my-token",
            org="test_org",
            bucket="test_bucket",
        )

        mock_cls.assert_called_once_with(
            url="http://localhost:8086",
            token="my-token",
            org="test_org",
        )

    @patch("app.services.influx_client.InfluxDBClient")
    def test_org_and_bucket_properties(self, mock_cls) -> None:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        client = InfluxClient(
            url="http://localhost:8086",
            token="my-token",
            org="my_org",
            bucket="my_bucket",
        )

        assert client.org == "my_org"
        assert client.bucket == "my_bucket"


class TestWritePoint:
    """Tests for InfluxClient.write_point."""

    @patch("app.services.influx_client.InfluxDBClient")
    def test_write_point_calls_write_api(self, mock_cls) -> None:
        mock_instance = MagicMock()
        mock_write_api = MagicMock()
        mock_instance.write_api.return_value = mock_write_api
        mock_instance.query_api.return_value = MagicMock()
        mock_cls.return_value = mock_instance

        client = InfluxClient(
            url="http://localhost:8086",
            token="token",
            org="org",
            bucket="bucket",
        )

        ts = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        client.write_point(
            measurement="microclimate",
            tags={"group_id": "g1", "metric": "temperature"},
            fields={"value": 22.5, "quality": "ok"},
            timestamp=ts,
        )

        mock_write_api.write.assert_called_once()
        call_args = mock_write_api.write.call_args
        assert call_args[1]["bucket"] == "bucket"
        assert call_args[1]["org"] == "org"
        record = call_args[1]["record"]
        assert record is not None

    @patch("app.services.influx_client.InfluxDBClient")
    def test_write_point_with_all_tag_types(self, mock_cls) -> None:
        mock_instance = MagicMock()
        mock_write_api = MagicMock()
        mock_instance.write_api.return_value = mock_write_api
        mock_instance.query_api.return_value = MagicMock()
        mock_cls.return_value = mock_instance

        client = InfluxClient(
            url="http://localhost:8086",
            token="token",
            org="org",
            bucket="bucket",
        )

        ts = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        client.write_point(
            measurement="microclimate",
            tags={
                "group_id": "group-001",
                "greenhouse_id": "gh-001",
                "zone_id": "zone-01",
                "sensor_id": "temp-01",
                "metric": "temperature",
            },
            fields={"value": 22.5, "quality": "ok"},
            timestamp=ts,
        )

        mock_write_api.write.assert_called_once()


class TestQuery:
    """Tests for InfluxClient.query and query_data."""

    @patch("app.services.influx_client.InfluxDBClient")
    def test_query_calls_query_api(self, mock_cls) -> None:
        mock_instance = MagicMock()
        mock_query_api = MagicMock()
        mock_instance.query_api.return_value = mock_query_api
        mock_query_api.query.return_value = []
        mock_instance.write_api.return_value = MagicMock()
        mock_cls.return_value = mock_instance

        client = InfluxClient(
            url="http://localhost:8086",
            token="token",
            org="org",
            bucket="bucket",
        )

        client.query('from(bucket: "bucket") |> range(start: -1h)')
        mock_query_api.query.assert_called_once()

    @patch("app.services.influx_client.InfluxDBClient")
    def test_query_data_returns_list_of_dicts(self, mock_cls) -> None:
        mock_instance = MagicMock()
        mock_query_api = MagicMock()
        mock_instance.query_api.return_value = mock_query_api
        mock_instance.write_api.return_value = MagicMock()

        # Create mock table with mock records
        mock_record = MagicMock()
        mock_record.values = {"_time": "2025-01-15T12:00:00Z", "_value": 22.5}
        mock_table = MagicMock()
        mock_table.records = [mock_record]
        mock_query_api.query.return_value = [mock_table]

        mock_cls.return_value = mock_instance

        client = InfluxClient(
            url="http://localhost:8086",
            token="token",
            org="org",
            bucket="bucket",
        )

        result = client.query_data('from(bucket: "bucket") |> range(start: -1h)')
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["_value"] == 22.5

    @patch("app.services.influx_client.InfluxDBClient")
    def test_query_data_empty_results(self, mock_cls) -> None:
        mock_instance = MagicMock()
        mock_query_api = MagicMock()
        mock_instance.query_api.return_value = mock_query_api
        mock_query_api.query.return_value = []
        mock_instance.write_api.return_value = MagicMock()
        mock_cls.return_value = mock_instance

        client = InfluxClient(
            url="http://localhost:8086",
            token="token",
            org="org",
            bucket="bucket",
        )

        result = client.query_data('from(bucket: "bucket") |> range(start: -1h)')
        assert result == []


class TestClose:
    """Tests for InfluxClient.close."""

    @patch("app.services.influx_client.InfluxDBClient")
    def test_close_calls_client_close(self, mock_cls) -> None:
        mock_instance = MagicMock()
        mock_instance.write_api.return_value = MagicMock()
        mock_instance.query_api.return_value = MagicMock()
        mock_cls.return_value = mock_instance

        client = InfluxClient(
            url="http://localhost:8086",
            token="token",
            org="org",
            bucket="bucket",
        )

        client.close()
        mock_instance.close.assert_called_once()


class TestRepositoryWithClient:
    """Tests for TelemetryRepository using the InfluxClient wrapper."""

    @patch("app.services.influx_client.InfluxDBClient")
    def test_write_telemetry_uses_influx_client(self, mock_cls) -> None:
        mock_instance = MagicMock()
        mock_write_api = MagicMock()
        mock_instance.write_api.return_value = mock_write_api
        mock_instance.query_api.return_value = MagicMock()
        mock_cls.return_value = mock_instance

        client = InfluxClient(
            url="http://localhost:8086",
            token="token",
            org="org",
            bucket="microclimate",
        )

        repo = TelemetryRepository(client)

        reading = TelemetryReading(
            group_id="group-001",
            greenhouse_id="gh-001",
            zone_id="zone-01",
            sensor_id="temp-01",
            metric="temperature",
            value=22.5,
            quality=Quality.OK,
            timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )

        repo.write_telemetry(reading)
        mock_write_api.write.assert_called_once()

    @patch("app.services.influx_client.InfluxDBClient")
    def test_get_latest_queries_with_correct_bucket(self, mock_cls) -> None:
        mock_instance = MagicMock()
        mock_query_api = MagicMock()
        mock_query_api.query.return_value = []
        mock_instance.query_api.return_value = mock_query_api
        mock_instance.write_api.return_value = MagicMock()
        mock_cls.return_value = mock_instance

        client = InfluxClient(
            url="http://localhost:8086",
            token="token",
            org="org",
            bucket="my_custom_bucket",
        )

        repo = TelemetryRepository(client)
        repo.get_latest("group-001")

        flux_query = mock_query_api.query.call_args[0][0]
        assert "my_custom_bucket" in flux_query
