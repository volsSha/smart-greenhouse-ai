"""Dashboard page -- fleet overview with real-time telemetry display.

Renders group overview cards, greenhouse detail views with zone charts,
and an alert panel. Handles loading, empty, and error states explicitly.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from nicegui import ui

from app.i18n.core import _
from app.ui.api_client import api_client

from app.ui.components.alert_panel import alert_panel
from app.ui.components.telemetry_cards import (
    group_overview_card,
    greenhouse_card,
    zone_detail_card,
)
from app.ui.components.telemetry_charts import (
    temperature_chart,
    humidity_chart,
    soil_moisture_chart,
    multi_metric_chart,
)
from app.ui.layouts.main_layout import main_layout

logger = logging.getLogger(__name__)

# Default group to display when no selection is made
_DEFAULT_GROUP_ID = "group-001"


# ---------------------------------------------------------------------------
# Data transformation (pure functions, tested separately)
# ---------------------------------------------------------------------------


def transform_latest_to_greenhouses(
    readings: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Transform flat latest readings into a greenhouse-grouped structure.

    Returns a dict keyed by greenhouse_id, each containing a metrics dict
    of the latest values per metric, plus zone and group metadata.
    """
    greenhouses: dict[str, dict[str, Any]] = {}

    for r in readings:
        gh_id = r.get("greenhouse_id", "unknown")
        zone_id = r.get("zone_id", "")
        metric = r.get("metric", "")

        if gh_id not in greenhouses:
            greenhouses[gh_id] = {
                "greenhouse_id": gh_id,
                "group_id": r.get("group_id", ""),
                "zones": set(),
                "metrics": {},
            }

        greenhouses[gh_id]["zones"].add(zone_id)

        # Take the latest value per metric (readings are pre-sorted desc)
        if metric not in greenhouses[gh_id]["metrics"]:
            greenhouses[gh_id]["metrics"][metric] = r.get("_value", r.get("value", 0))

    # Convert sets to lists for serialization
    for gh in greenhouses.values():
        gh["zone_count"] = len(gh.pop("zones"))

    return greenhouses


def transform_latest_to_zones(
    readings: list[dict[str, Any]],
    greenhouse_id: str,
) -> list[dict[str, Any]]:
    """Transform flat readings into zone-level structures for one greenhouse.

    Returns a list of zone dicts, each with a metrics dict.
    """
    zones: dict[str, dict[str, Any]] = {}

    for r in readings:
        if r.get("greenhouse_id") != greenhouse_id:
            continue
        zone_id = r.get("zone_id", "")
        metric = r.get("metric", "")

        if zone_id not in zones:
            zones[zone_id] = {
                "zone_id": zone_id,
                "greenhouse_id": greenhouse_id,
                "metrics": {},
            }

        if metric not in zones[zone_id]["metrics"]:
            zones[zone_id]["metrics"][metric] = r.get("_value", r.get("value", 0))

    return list(zones.values())


def build_group_data(
    greenhouses: dict[str, dict[str, Any]],
    anomalies: list[dict[str, Any]],
    group_id: str,
) -> dict[str, Any]:
    """Build group overview data from greenhouse and anomaly data."""
    return {
        "group_id": group_id,
        "name": group_id,
        "greenhouse_count": len(greenhouses),
        "active_alerts": len(anomalies),
    }


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------


@ui.page("/dashboard")
async def dashboard() -> None:
    """Render the fleet dashboard page."""
    main_layout()

    ui.label(_("Dashboard")).classes("text-2xl font-bold mt-6")

    # State containers
    content_area = ui.column().classes("w-full gap-4 mt-4")
    selected_gh: dict[str, Any] = {"id": None}

    async def load_data() -> None:
        """Fetch telemetry data and render dashboard content."""
        content_area.clear()

        try:
            async with api_client(timeout=10.0) as client:
                latest_resp, anomalies_resp = await asyncio.gather(
                    client.get(f"/api/groups/{_DEFAULT_GROUP_ID}/telemetry/latest"),
                    client.get(f"/api/groups/{_DEFAULT_GROUP_ID}/telemetry/anomalies"),
                )
                latest_resp.raise_for_status()
                anomalies_resp.raise_for_status()
                latest_data = latest_resp.json()
                anomalies_data = anomalies_resp.json()

        except httpx.HTTPError as exc:
            ui.label(_("Error loading data: {error}", error=exc)).classes("text-red-500 text-sm")
            ui.label(
                _("Make sure the API is running and InfluxDB is available.")
            ).classes("text-xs opacity-50 mt-1")
            return

        readings = latest_data.get("readings", [])
        anomalies = anomalies_data.get("anomalies", [])

        if not readings:
            with ui.column().classes("w-full items-center gap-4 mt-20"):
                ui.icon("sensors_off", size="4rem").classes("opacity-30")
                ui.label(_("No telemetry data available")).classes("text-lg opacity-50")
                ui.label(
                    _("Start the simulator to generate data and see it here.")
                ).classes("text-sm opacity-40")
            return

        # Transform data
        greenhouses = transform_latest_to_greenhouses(readings)
        group_data = build_group_data(greenhouses, anomalies, _DEFAULT_GROUP_ID)

        # --- Group overview ---
        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("w-2/3"):
                group_overview_card(group_data)

            with ui.column().classes("w-1/3"):
                alert_panel(anomalies)

        # --- Greenhouse cards ---
        ui.label(_("Greenhouses")).classes("text-lg font-bold mt-2")
        with ui.row().classes("w-full gap-4 flex-wrap"):
            for gh_id, gh_data in greenhouses.items():
                column = ui.column().classes("w-64 cursor-pointer")
                column.on("click", lambda gh=gh_id: select_greenhouse(gh))
                with column:
                    greenhouse_card(gh_data)

        # --- Zone detail area (hidden initially) ---
        zone_detail_container = ui.column().classes("w-full gap-4 mt-4")
        zone_detail_container.set_visibility(False)

        async def select_greenhouse(gh_id: str) -> None:
            """Show zone detail for a selected greenhouse."""
            selected_gh["id"] = gh_id
            zone_detail_container.clear()
            zone_detail_container.set_visibility(True)

            ui.label(_("Greenhouse: {greenhouse_id}", greenhouse_id=gh_id)).classes("text-lg font-bold")

            zones = transform_latest_to_zones(readings, gh_id)

            if not zones:
                ui.label(_("No zone data available")).classes("text-sm opacity-50")
                return

            # Zone detail cards
            with ui.row().classes("w-full gap-4 flex-wrap"):
                for zone in zones:
                    zone_detail_card(zone)

            # Zone charts -- fetch historical data
            with content_area:
                ui.separator().classes("w-full mt-2")
                ui.label(_("Zone Charts")).classes("text-lg font-bold mt-2")

            try:
                async with api_client(timeout=10.0) as client:
                    now = datetime.now(timezone.utc)
                    start = (now - timedelta(hours=6)).isoformat()
                    end = now.isoformat()

                    range_resp = await client.get(
                        f"/api/groups/{_DEFAULT_GROUP_ID}/telemetry/range",
                        params={
                            "start": start,
                            "end": end,
                            "greenhouse_id": gh_id,
                            "limit": 500,
                        },
                    )
                    range_resp.raise_for_status()
                    range_data = range_resp.json()
                    range_readings = range_data.get("readings", [])

                    if range_readings:
                        # Separate readings by metric for individual charts
                        temp_readings = [
                            r for r in range_readings if r.get("metric") == "temperature"
                        ]
                        humidity_readings = [
                            r for r in range_readings if r.get("metric") == "air_humidity"
                        ]
                        soil_readings = [
                            r for r in range_readings if r.get("metric") == "soil_moisture"
                        ]

                        with ui.row().classes("w-full gap-4 flex-wrap"):
                            if temp_readings:
                                with ui.column().classes("w-1/3 min-w-[300px]"):
                                    temperature_chart(temp_readings)
                            if humidity_readings:
                                with ui.column().classes("w-1/3 min-w-[300px]"):
                                    humidity_chart(humidity_readings)
                            if soil_readings:
                                with ui.column().classes("w-1/3 min-w-[300px]"):
                                    soil_moisture_chart(soil_readings)

                        # Multi-metric chart
                        with ui.row().classes("w-full mt-4"):
                            multi_metric_chart(range_readings)
                    else:
                        ui.label(_("No historical data for charts")).classes("text-sm opacity-50")

            except httpx.HTTPError as exc:
                ui.label(_("Error loading chart data: {error}", error=exc)).classes("text-red-500 text-xs")

    # Initial load
    await load_data()
