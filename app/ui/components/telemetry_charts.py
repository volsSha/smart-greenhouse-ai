"""Telemetry chart components for the Smart Greenhouse dashboard.

Provides ECharts-based line charts for temperature, humidity,
soil moisture, and configurable multi-metric displays.
"""

from __future__ import annotations

from typing import Any, Literal

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


ChartSize = Literal["compact", "normal", "expanded"]

_CHART_SIZE_CLASSES: dict[ChartSize, str] = {
    "compact": "h-56",
    "normal": "h-80",
    "expanded": "h-[28rem]",
}


def _parse_readings(readings: list[dict[str, Any]]) -> list[list[Any]]:
    points: list[list[Any]] = []

    sorted_readings = sorted(
        readings,
        key=lambda r: r.get("_time", r.get("timestamp", "")),
    )

    for reading in sorted_readings:
        ts = str(reading.get("_time", reading.get("timestamp", "")))
        val = reading.get("_value", reading.get("value", 0))
        points.append([ts, float(val)])

    return points


def chart_size_class(size: ChartSize = "normal") -> str:
    return f"w-full {_CHART_SIZE_CLASSES.get(size, _CHART_SIZE_CLASSES['normal'])}"


def _build_line_option(
    title: str,
    series_data: list[dict[str, Any]],
    y_unit: str = "",
) -> dict[str, Any]:
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
            "bottom": "20%",
            "containLabel": True,
        },
        "toolbox": {
            "feature": {"restore": {}, "saveAsImage": {}},
            "right": 12,
        },
        "dataZoom": [
            {"type": "inside", "throttle": 50},
            {"type": "slider", "bottom": 28},
        ],
        "xAxis": {
            "type": "time",
            "axisLabel": {
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
                "showSymbol": False,
                "itemStyle": {"color": s.get("color", "#3498db")},
                "lineStyle": {"width": 2},
            }
            for s in series_data
        ],
    }


# ---------------------------------------------------------------------------
# Public chart components
# ---------------------------------------------------------------------------


def temperature_chart(readings: list[dict[str, Any]], size: ChartSize = "normal") -> ui.echart:
    points = _parse_readings(readings)
    option = _build_line_option(
        title=_("Temperature"),
        series_data=[{"name": _("Temperature"), "data": points, "color": _METRIC_COLORS["temperature"]}],
        y_unit="C",
    )
    return ui.echart(option).classes(chart_size_class(size))


def humidity_chart(readings: list[dict[str, Any]], size: ChartSize = "normal") -> ui.echart:
    points = _parse_readings(readings)
    option = _build_line_option(
        title=_("Air Humidity"),
        series_data=[{"name": _("Humidity"), "data": points, "color": _METRIC_COLORS["air_humidity"]}],
        y_unit="%",
    )
    return ui.echart(option).classes(chart_size_class(size))


def soil_moisture_chart(readings: list[dict[str, Any]], size: ChartSize = "normal") -> ui.echart:
    points = _parse_readings(readings)
    option = _build_line_option(
        title=_("Soil Moisture"),
        series_data=[{"name": _("Soil Moisture"), "data": points, "color": _METRIC_COLORS["soil_moisture"]}],
        y_unit="%",
    )
    return ui.echart(option).classes(chart_size_class(size))


def _series_label(reading: dict[str, Any], metric_name: str) -> str:
    zone_id = reading.get("zone_id")
    if zone_id:
        return _("{metric} / {zone_id}", metric=_metric_label(metric_name), zone_id=zone_id)
    return _metric_label(metric_name)


def multi_metric_chart(
    readings: list[dict[str, Any]],
    metrics: list[str] | None = None,
    size: ChartSize = "normal",
) -> ui.echart:
    if not readings:
        return ui.echart({"title": {"text": _("No data")}}).classes(chart_size_class(size))

    grouped: dict[str, list[dict[str, Any]]] = {}
    labels: dict[str, str] = {}
    for reading in readings:
        metric = reading.get("metric", "unknown")
        if metrics and metric not in metrics:
            continue
        series_key = f"{metric}:{reading.get('zone_id', '')}"
        grouped.setdefault(series_key, []).append(reading)
        labels.setdefault(series_key, _series_label(reading, metric))

    series_data: list[dict[str, Any]] = []
    for series_key, metric_readings in grouped.items():
        metric_name = metric_readings[0].get("metric", "unknown")
        series_data.append({
            "name": labels[series_key],
            "data": _parse_readings(metric_readings),
            "color": _METRIC_COLORS.get(metric_name, "#95a5a6"),
        })

    option = _build_line_option(
        title=_("Metrics Overview"),
        series_data=series_data,
    )
    return ui.echart(option).classes(chart_size_class(size))
