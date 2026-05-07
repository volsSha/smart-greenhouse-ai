"""Telemetry repository for InfluxDB read/write operations.

Provides methods to persist telemetry readings and query aggregated
summaries, historical ranges, anomaly detection, and cross-greenhouse
comparisons from the ``microclimate`` measurement.

Measurement format (from DATABASE.md):
    measurement: ``microclimate``
    tags: group_id, greenhouse_id, zone_id, sensor_id, metric
    fields: value (float), quality (string)
    time: timestamp
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.schemas.telemetry import TelemetryReading

logger = logging.getLogger(__name__)


class TelemetryRepository:
    """Repository for InfluxDB telemetry operations.

    Parameters:
        influx_client: An :class:`app.services.influx_client.InfluxClient`
            instance used for all reads and writes.
    """

    def __init__(self, influx_client: Any) -> None:
        self._client = influx_client

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write_telemetry(self, reading: TelemetryReading) -> None:
        """Persist a validated telemetry reading to InfluxDB.

        Parameters:
            reading: A :class:`TelemetryReading` to store.
        """
        self._client.write_point(
            measurement="microclimate",
            tags={
                "group_id": reading.group_id,
                "greenhouse_id": reading.greenhouse_id,
                "zone_id": reading.zone_id,
                "sensor_id": reading.sensor_id,
                "metric": reading.metric,
            },
            fields={
                "value": reading.value,
                "quality": reading.quality.value
                if hasattr(reading.quality, "value")
                else reading.quality,
            },
            timestamp=reading.timestamp,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_latest(
        self,
        group_id: str,
        greenhouse_id: str | None = None,
        zone_id: str | None = None,
        metric: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get the latest readings for a group (optionally filtered).

        Returns the most recent value per metric/sensor combination.
        """
        filters = [f'r.group_id == "{group_id}"']
        if greenhouse_id:
            filters.append(f'r.greenhouse_id == "{greenhouse_id}"')
        if zone_id:
            filters.append(f'r.zone_id == "{zone_id}"')
        if metric:
            filters.append(f'r.metric == "{metric}"')

        filter_clause = " and ".join(filters)

        flux = f"""
        from(bucket: "{self._client.bucket}")
          |> range(start: -1h)
          |> filter(fn: (r) => {filter_clause})
          |> last()
          |> sort(columns: ["_time"], desc: true)
        """
        return self._client.query_data(flux)

    def get_group_summary(
        self,
        group_id: str,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> list[dict[str, Any]]:
        """Get min/max/avg/latest per metric for an entire group.

        Parameters:
            group_id: The group to summarize.
            date_range: Optional (start, end) tuple. Defaults to today.
        """
        start, end = self._resolve_date_range(date_range)
        flux = f"""
        from(bucket: "{self._client.bucket}")
          |> range(start: {start}, stop: {end})
          |> filter(fn: (r) => r.group_id == "{group_id}" and r._field == "value")
          |> group(columns: ["metric"])
          |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
          |> group()
          |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
          |> group(columns: ["metric"])
          |> min(column: "_value")
          |> yield(name: "min")
        """
        min_results = self._client.query_data(flux)

        flux_max = flux.replace('yield(name: "min")', 'yield(name: "max")')
        flux_max = flux_max.replace("|> min(column: \"_value\")", "|> max(column: \"_value\")")
        max_results = self._client.query_data(flux_max)

        return self._merge_summaries(min_results, max_results)

    def get_greenhouse_summary(
        self,
        group_id: str,
        greenhouse_id: str,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> list[dict[str, Any]]:
        """Get min/max/avg/latest per metric for a specific greenhouse."""
        start, end = self._resolve_date_range(date_range)

        flux = f"""
        from(bucket: "{self._client.bucket}")
          |> range(start: {start}, stop: {end})
          |> filter(fn: (r) =>
              r.group_id == "{group_id}"
              and r.greenhouse_id == "{greenhouse_id}"
              and r._field == "value"
          )
          |> group(columns: ["metric"])
          |> min(column: "_value")
        """
        min_results = self._client.query_data(flux)

        flux_max = flux.replace(
            '|> min(column: "_value")', '|> max(column: "_value")'
        )
        max_results = self._client.query_data(flux_max)

        flux_last = flux.replace(
            '|> min(column: "_value")', '|> last(column: "_value")'
        )
        last_results = self._client.query_data(flux_last)

        return self._merge_summaries(
            min_results, max_results, last_results
        )

    def get_zone_summary(
        self,
        group_id: str,
        greenhouse_id: str,
        zone_id: str,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> list[dict[str, Any]]:
        """Get min/max/avg/latest per metric for a specific zone."""
        start, end = self._resolve_date_range(date_range)

        flux = f"""
        from(bucket: "{self._client.bucket}")
          |> range(start: {start}, stop: {end})
          |> filter(fn: (r) =>
              r.group_id == "{group_id}"
              and r.greenhouse_id == "{greenhouse_id}"
              and r.zone_id == "{zone_id}"
              and r._field == "value"
          )
          |> group(columns: ["metric"])
          |> min(column: "_value")
        """
        min_results = self._client.query_data(flux)

        flux_max = flux.replace(
            '|> min(column: "_value")', '|> max(column: "_value")'
        )
        max_results = self._client.query_data(flux_max)

        flux_last = flux.replace(
            '|> min(column: "_value")', '|> last(column: "_value")'
        )
        last_results = self._client.query_data(flux_last)

        return self._merge_summaries(
            min_results, max_results, last_results
        )

    def get_range(
        self,
        group_id: str,
        start: datetime,
        end: datetime,
        greenhouse_id: str | None = None,
        zone_id: str | None = None,
        metric: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Get historical telemetry readings within a time range.

        Parameters:
            group_id: Group to query.
            start: Start of the time range.
            end: End of the time range.
            greenhouse_id: Optional greenhouse filter.
            zone_id: Optional zone filter.
            metric: Optional metric filter.
            limit: Maximum number of records to return.
        """
        filters = [f'r.group_id == "{group_id}"', 'r._field == "value"']
        if greenhouse_id:
            filters.append(f'r.greenhouse_id == "{greenhouse_id}"')
        if zone_id:
            filters.append(f'r.zone_id == "{zone_id}"')
        if metric:
            filters.append(f'r.metric == "{metric}"')

        filter_clause = " and ".join(filters)

        start_str = self._format_datetime(start)
        end_str = self._format_datetime(end)

        flux = f"""
        from(bucket: "{self._client.bucket}")
          |> range(start: {start_str}, stop: {end_str})
          |> filter(fn: (r) => {filter_clause})
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {limit})
        """
        return self._client.query_data(flux)

    def get_anomalies(
        self,
        group_id: str,
    ) -> list[dict[str, Any]]:
        """Simple threshold-based anomaly detection.

        Returns readings where values deviate significantly from the
        group mean (more than 3 standard deviations) for each metric.
        """
        flux = f"""
        data = from(bucket: "{self._client.bucket}")
          |> range(start: -24h)
          |> filter(fn: (r) => r.group_id == "{group_id}" and r._field == "value")
          |> group(columns: ["metric"])

        mean_val = data |> mean(column: "_value")
        std_val = data |> stddev(column: "_value")

        anomalies = data
          |> join(
              tables: {{m: mean_val, s: std_val}},
              on: ["metric"],
              method: "inner"
          )
          |> filter(fn: (r) =>
              r._value_m != 0.0 and
              math.abs(x: (r._value - r._value_m) / r._value_s) > 3.0
          )
          |> yield(name: "anomalies")
        """
        return self._client.query_data(flux)

    def compare_greenhouses(
        self,
        group_id: str,
    ) -> list[dict[str, Any]]:
        """Compare current conditions across all greenhouses in a group.

        Returns the latest average value per metric per greenhouse,
        allowing side-by-side comparison.
        """
        flux = f"""
        from(bucket: "{self._client.bucket}")
          |> range(start: -1h)
          |> filter(fn: (r) =>
              r.group_id == "{group_id}"
              and r._field == "value"
          )
          |> group(columns: ["greenhouse_id", "metric"])
          |> mean(column: "_value")
          |> group(columns: ["metric"])
          |> sort(columns: ["greenhouse_id"])
        """
        return self._client.query_data(flux)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_date_range(
        date_range: tuple[datetime, datetime] | None,
    ) -> tuple[str, str]:
        """Resolve a date range to Flux-compatible time strings.

        If no range is provided, defaults to today (UTC midnight to now).
        """
        if date_range is not None:
            start_str = TelemetryRepository._format_datetime(date_range[0])
            end_str = TelemetryRepository._format_datetime(date_range[1])
            return start_str, end_str

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_str = TelemetryRepository._format_datetime(today_start)
        end_str = TelemetryRepository._format_datetime(now + timedelta(seconds=1))
        return start_str, end_str

    @staticmethod
    def _format_datetime(dt: datetime) -> str:
        """Format a datetime as a Flux timestamp string."""
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _merge_summaries(
        min_results: list[dict[str, Any]],
        max_results: list[dict[str, Any]],
        last_results: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Merge min/max/last query results into summary records.

        Groups results by metric and produces a dict with min, max,
        and optionally latest value per metric.
        """
        summaries: dict[str, dict[str, Any]] = {}

        for row in min_results:
            metric = row.get("metric", "unknown")
            summaries.setdefault(metric, {})["min"] = row.get("_value")

        for row in max_results:
            metric = row.get("metric", "unknown")
            summaries.setdefault(metric, {})["max"] = row.get("_value")

        if last_results:
            for row in last_results:
                metric = row.get("metric", "unknown")
                summaries.setdefault(metric, {})["latest"] = row.get("_value")

        return [
            {"metric": metric, **stats}
            for metric, stats in summaries.items()
        ]
