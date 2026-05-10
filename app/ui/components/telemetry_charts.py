"""Telemetry chart components for the Smart Greenhouse dashboard.

Provides ECharts-based line charts for temperature, humidity,
soil moisture, and configurable multi-metric displays.
"""

from __future__ import annotations

from typing import Any

from nicegui import ui

from app.i18n.core import _


# ---------------------------------------------------------------------------
# Color palette for metrics
# ---------------------------------------------------------------------------

_METRIC_COLORS: dict[str, str] = {
    "temperature": "#e74c3c",
    "air_humidity": "#3498db",
    "soil_moisture": "#8b6914",
    "co2": "#9b59b6",
    "light": "#f1c40f",
    "fan_power": "#1abc9c",
    "pump_state": "#2ecc71",
    "heater_power": "#e67e22",
    "lamp_state": "#f39c12",
}

_METRIC_UNITS: dict[str, str] = {
    "temperature": "C",
    "air_humidity": "%",
    "soil_moisture": "%",
    "co2": "ppm",
    "light": "lux",
    "fan_power": "%",
    "pump_state": "",
    "heater_power": "%",
    "lamp_state": "",
}


def _metric_label(metric_name: str) -> str:
    labels = {
        "temperature": _("Temperature"),
        "air_humidity": _("Air Humidity"),
        "soil_moisture": _("Soil Moisture"),
        "co2": _("CO2"),
        "light": _("Light"),
        "fan_power": _("Fan"),
        "pump_state": _("Pump"),
        "heater_power": _("Heater"),
        "lamp_state": _("Lamp"),
    }
    return labels.get(metric_name, metric_name.replace("_", " ").title())


def _parse_readings(readings: list[dict[str, Any]]) -> tuple[list[str], list[float]]:
    """Extract timestamps and values from raw InfluxDB query results.

    Returns (timestamps, values) lists sorted by time ascending.
    """
    timestamps: list[str] = []
    values: list[float] = []

    sorted_readings = sorted(
        readings,
        key=lambda r: r.get("_time", r.get("timestamp", "")),
    )

    for reading in sorted_readings:
        ts = reading.get("_time", reading.get("timestamp", ""))
        val = reading.get("_value", reading.get("value", 0))
        timestamps.append(str(ts))
        values.append(float(val))

    return timestamps, values


def _build_line_option(
    title: str,
    timestamps: list[str],
    series_data: list[dict[str, Any]],
    y_unit: str = "",
) -> dict[str, Any]:
    """Build an ECharts option dict for a line chart.

    Parameters:
        title: Chart title.
        timestamps: X-axis time labels.
        series_data: List of dicts with 'name' and 'data' keys.
        y_unit: Unit label for the Y axis.
    """
    return {
        "title": {
            "text": title,
            "textStyle": {"fontSize": 14},
            "left": "center",
        },
        "tooltip": {
            "trigger": "axis",
        },
        "legend": {
            "data": [s["name"] for s in series_data],
            "bottom": 0,
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": timestamps,
            "axisLabel": {
                "rotate": 30,
                "fontSize": 10,
            },
        },
        "yAxis": {
            "type": "value",
            "name": y_unit,
            "nameTextStyle": {"fontSize": 11},
        },
        "series": [
            {
                "name": s["name"],
                "type": "line",
                "data": s["data"],
                "smooth": True,
                "itemStyle": {"color": s.get("color", "#3498db")},
                "lineStyle": {"width": 2},
            }
            for s in series_data
        ],
    }


# ---------------------------------------------------------------------------
# Public chart components
# ---------------------------------------------------------------------------


def temperature_chart(readings: list[dict[str, Any]]) -> ui.echart:
    """Render a line chart of temperature over time.

    Parameters:
        readings: Raw InfluxDB query results with ``_time`` and ``_value`` fields.

    Returns:
        The EChart element for later updates.
    """
    timestamps, values = _parse_readings(readings)
    option = _build_line_option(
        title=_("Temperature"),
        timestamps=timestamps,
        series_data=[{"name": _("Temperature"), "data": values, "color": _METRIC_COLORS["temperature"]}],
        y_unit="C",
    )
    return ui.echart(option).classes("w-full h-64")


def humidity_chart(readings: list[dict[str, Any]]) -> ui.echart:
    """Render a line chart of humidity over time.

    Parameters:
        readings: Raw InfluxDB query results with ``_time`` and ``_value`` fields.

    Returns:
        The EChart element for later updates.
    """
    timestamps, values = _parse_readings(readings)
    option = _build_line_option(
        title=_("Air Humidity"),
        timestamps=timestamps,
        series_data=[{"name": _("Humidity"), "data": values, "color": _METRIC_COLORS["air_humidity"]}],
        y_unit="%",
    )
    return ui.echart(option).classes("w-full h-64")


def soil_moisture_chart(readings: list[dict[str, Any]]) -> ui.echart:
    """Render a line chart of soil moisture over time.

    Parameters:
        readings: Raw InfluxDB query results with ``_time`` and ``_value`` fields.

    Returns:
        The EChart element for later updates.
    """
    timestamps, values = _parse_readings(readings)
    option = _build_line_option(
        title=_("Soil Moisture"),
        timestamps=timestamps,
        series_data=[{"name": _("Soil Moisture"), "data": values, "color": _METRIC_COLORS["soil_moisture"]}],
        y_unit="%",
    )
    return ui.echart(option).classes("w-full h-64")


def multi_metric_chart(
    readings: list[dict[str, Any]],
    metrics: list[str] | None = None,
) -> ui.echart:
    """Render a configurable multi-metric line chart.

    Groups readings by the ``metric`` tag and renders one line per metric.
    Falls back to all detected metrics if *metrics* is None.

    Parameters:
        readings: Raw InfluxDB query results with ``_time``, ``_value``,
            and ``metric`` fields.
        metrics: Subset of metric names to display. None = all detected.

    Returns:
        The EChart element for later updates.
    """
    if not readings:
        return ui.echart({"title": {"text": _("No data")}}).classes("w-full h-64")

    # Group readings by metric
    grouped: dict[str, list[dict[str, Any]]] = {}
    for reading in readings:
        metric = reading.get("metric", "unknown")
        if metrics and metric not in metrics:
            continue
        grouped.setdefault(metric, []).append(reading)

    # Build series
    series_data: list[dict[str, Any]] = []
    all_timestamps: list[str] = []

    for metric_name, metric_readings in grouped.items():
        ts, vals = _parse_readings(metric_readings)
        if ts and not all_timestamps:
            all_timestamps = ts
        series_data.append({
            "name": _metric_label(metric_name),
            "data": vals,
            "color": _METRIC_COLORS.get(metric_name, "#95a5a6"),
        })

    option = _build_line_option(
        title=_("Metrics Overview"),
        timestamps=all_timestamps,
        series_data=series_data,
    )
    return ui.echart(option).classes("w-full h-64")
