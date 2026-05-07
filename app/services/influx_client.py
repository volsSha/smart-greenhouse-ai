"""InfluxDB 2.7 client wrapper for telemetry persistence and queries.

Wraps ``influxdb_client.InfluxDBClient`` to provide a simplified interface
for writing data points and executing Flux queries. Configuration is read
from :class:`app.config.InfluxDBSettings` via the application settings.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.query_api import TableList

logger = logging.getLogger(__name__)


class InfluxClient:
    """High-level wrapper around the InfluxDB 2.7 Python client.

    Parameters:
        url: InfluxDB server URL (e.g. ``http://localhost:8086``).
        token: Authentication token.
        org: Organization name.
        bucket: Default bucket for writes and queries.
    """

    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str,
    ) -> None:
        self._org = org
        self._bucket = bucket
        self._client = InfluxDBClient(url=url, token=token, org=org)
        self._write_api = self._client.write_api()
        self._query_api = self._client.query_api()
        logger.info(
            "InfluxClient initialized (org=%s, bucket=%s)", org, bucket
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_point(
        self,
        measurement: str,
        tags: dict[str, str],
        fields: dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Write a single data point to the default bucket.

        Parameters:
            measurement: InfluxDB measurement name (e.g. ``"microclimate"``).
            tags: Tag key-value pairs (indexed).
            fields: Field key-value pairs (not indexed).
            timestamp: Point timestamp (must be timezone-aware).
        """
        point = Point(measurement)
        for key, value in tags.items():
            point.tag(key, str(value))
        for key, value in fields.items():
            point.field(key, value)
        point.time(timestamp, WritePrecision.NS)

        self._write_api.write(
            bucket=self._bucket,
            org=self._org,
            record=point,
        )
        logger.debug(
            "Wrote point to %s: tags=%s fields=%s ts=%s",
            measurement,
            tags,
            fields,
            timestamp.isoformat(),
        )

    def query(self, flux_query: str) -> TableList:
        """Execute a Flux query and return raw results.

        Parameters:
            flux_query: A valid InfluxDB Flux query string.

        Returns:
            :class:`TableList` from the InfluxDB client.
        """
        logger.debug("Executing Flux query: %s", flux_query)
        result = self._query_api.query(flux_query, org=self._org)
        return result

    def query_data(self, flux_query: str) -> list[dict[str, Any]]:
        """Execute a Flux query and return results as plain dictionaries.

        Each row is returned as a dict with column names as keys.
        This is a convenience wrapper around :meth:`query` for cases
        where raw table structure is not needed.
        """
        tables = self.query(flux_query)
        rows: list[dict[str, Any]] = []
        for table in tables:
            for record in table.records:
                rows.append(record.values)
        return rows

    @property
    def org(self) -> str:
        return self._org

    @property
    def bucket(self) -> str:
        return self._bucket

    def close(self) -> None:
        """Close the InfluxDB client and release resources."""
        self._client.close()
        logger.info("InfluxClient closed")
