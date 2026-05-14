"""Telemetry card components for the Smart Greenhouse dashboard.

Provides NiceGUI card widgets for displaying group overviews,
greenhouse summaries, zone details, and metric indicators.
"""

from __future__ import annotations

from typing import Any

from nicegui import ui

from app.i18n.core import _


# ---------------------------------------------------------------------------
# Metric thresholds for status coloring
# ---------------------------------------------------------------------------

METRIC_THRESHOLDS: dict[str, dict[str, tuple[float, float]]] = {
    "temperature": {"green": (18, 28), "yellow": (14, 34)},
    "air_humidity": {"green": (40, 80), "yellow": (25, 90)},
    "soil_moisture": {"green": (30, 70), "yellow": (15, 85)},
    "co2": {"green": (300, 1000), "yellow": (200, 1500)},
    "light": {"green": (200, 10000), "yellow": (50, 50000)},
}


def _metric_status(metric: str, value: float) -> str:
    """Determine status color for a metric value.

    Returns 'green', 'yellow', or 'red' based on configured thresholds.
    Falls back to 'green' for unknown metrics.
    """
    thresholds = METRIC_THRESHOLDS.get(metric)
    if thresholds is None:
        return "green"
    green = thresholds.get("green", (0, 100))
    yellow = thresholds.get("yellow", (0, 100))
    if green[0] <= value <= green[1]:
        return "green"
    if yellow[0] <= value <= yellow[1]:
        return "yellow"
    return "red"


_STATUS_COLORS: dict[str, str] = {
    "green": "#4caf50",
    "yellow": "#ff9800",
    "red": "#f44336",
}


# ---------------------------------------------------------------------------
# Public card components
# ---------------------------------------------------------------------------


def metric_badge(
    label: str,
    value: float,
    unit: str,
    status: str | None = None,
) -> None:
    """Render a small colored metric indicator badge.

    Parameters:
        label: Metric display name (e.g. "Temperature").
        value: Numeric sensor value.
        unit: Unit suffix (e.g. "C", "%").
        status: Override status color. Auto-detected from thresholds if None.
    """
    if status is None:
        status = "green"

    color = _STATUS_COLORS.get(status, "#9e9e9e")

    with ui.row().classes("greenhouse-metric-row items-center gap-2"):
        ui.icon("circle", size="0.5rem").style(f"color: {color}")
        ui.label(_("{label}:", label=label)).classes("text-xs opacity-70")
        ui.label(f"{value:.1f} {unit}").classes("text-xs font-semibold")


def group_overview_card(group_data: dict[str, Any]) -> None:
    """Render a card summarizing a fleet group.

    Parameters:
        group_data: Dict with keys:
            - group_id (str)
            - name (str, optional)
            - greenhouse_count (int)
            - active_alerts (int, optional, default 0)
    """
    group_id = group_data.get("group_id", "unknown")
    name = group_data.get("name", group_id)
    greenhouse_count = group_data.get("greenhouse_count", 0)
    active_alerts = group_data.get("active_alerts", 0)

    with ui.card().classes("greenhouse-card w-full p-5"):
        with ui.row().classes("items-center justify-between w-full"):
            with ui.column().classes("gap-0"):
                ui.label(name).classes("text-xl font-bold")
                ui.label(group_id).classes("text-xs font-mono opacity-50")
            if active_alerts > 0:
                ui.badge(_("{count} alerts", count=active_alerts), color="red").props('outline')
            else:
                ui.badge(_("Healthy"), color="green").props('outline')

        with ui.row().classes("items-center gap-4 mt-4"):
            ui.icon("group", size="1.4rem").classes("opacity-55")
            ui.label(_("{count} greenhouses", count=greenhouse_count)).classes(
                "text-sm opacity-75"
            )


def greenhouse_card(greenhouse_data: dict[str, Any]) -> None:
    """Render a card summarizing a single greenhouse.

    Parameters:
        greenhouse_data: Dict with keys:
            - greenhouse_id (str)
            - name (str, optional)
            - zone_count (int, optional)
            - metrics (dict[str, float], optional): Latest metric values
    """
    gh_id = greenhouse_data.get("greenhouse_id", "unknown")
    name = greenhouse_data.get("name", gh_id)
    zone_count = greenhouse_data.get("zone_count", 0)
    metrics = greenhouse_data.get("metrics", {})

    with ui.card().classes("greenhouse-card greenhouse-interactive w-full p-4"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(name).classes("text-md font-bold")
            ui.icon("chevron_right", size="1.1rem").classes("opacity-35")

        if zone_count:
            ui.label(_("{count} zones", count=zone_count)).classes(
                "text-xs opacity-55 mt-1"
            )

        if metrics:
            with ui.column().classes("gap-1 mt-2"):
                for metric_name, metric_label, unit in [
                    ("temperature", _("Temp"), "C"),
                    ("air_humidity", _("Humidity"), "%"),
                    ("soil_moisture", _("Soil"), "%"),
                ]:
                    if metric_name in metrics:
                        value = metrics[metric_name]
                        status = _metric_status(metric_name, value)
                        metric_badge(metric_label, value, unit, status)
        else:
            ui.label(_("No recent data")).classes("text-xs italic opacity-50 mt-2")


def zone_detail_card(zone_data: dict[str, Any]) -> None:
    """Render a detailed card for a single zone with all metrics.

    Parameters:
        zone_data: Dict with keys:
            - zone_id (str)
            - name (str, optional)
            - metrics (dict[str, float]): Latest metric values
            - plant_batch (str, optional): Current plant batch name
            - growth_stage (str, optional): Current growth stage
    """
    zone_id = zone_data.get("zone_id", "unknown")
    name = zone_data.get("name", zone_id)
    metrics = zone_data.get("metrics", {})
    plant_batch = zone_data.get("plant_batch")
    growth_stage = zone_data.get("growth_stage")

    with ui.card().classes("greenhouse-card w-full p-4"):
        ui.label(name).classes("text-md font-bold")

        if plant_batch or growth_stage:
            with ui.row().classes("items-center gap-2 mt-1"):
                if plant_batch:
                    ui.label(plant_batch).classes("text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded")
                if growth_stage:
                    ui.label(growth_stage).classes("text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded")

        if metrics:
            with ui.column().classes("gap-1 mt-2"):
                metric_units: dict[str, tuple[str, str]] = {
                    "temperature": (_("Temperature"), "C"),
                    "air_humidity": (_("Humidity"), "%"),
                    "soil_moisture": (_("Soil Moisture"), "%"),
                    "co2": (_("CO2"), "ppm"),
                    "light": (_("Light"), "lux"),
                    "fan_power": (_("Fan"), "%"),
                    "pump_state": (_("Pump"), ""),
                    "heater_power": (_("Heater"), "%"),
                    "lamp_state": (_("Lamp"), ""),
                }
                for metric_name, (label, unit) in metric_units.items():
                    if metric_name in metrics:
                        value = metrics[metric_name]
                        status = _metric_status(metric_name, value)
                        metric_badge(label, value, unit, status)
        else:
            ui.label(_("No recent data")).classes("text-xs italic opacity-50 mt-2")
