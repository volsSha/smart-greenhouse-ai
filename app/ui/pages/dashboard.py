"""Dashboard page -- fleet overview with real-time telemetry display.

Renders group overview cards, greenhouse detail views with zone charts,
and an alert panel. Handles loading, empty, and error states explicitly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from nicegui import ui

from app.i18n.core import _
from app.ui.api_client import api_client

from app.ui.components.alert_panel import alert_panel
from app.ui.components.design import empty_state, page_container, page_hero, section_card
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

    with page_container():
        page_hero(
            _("Dashboard"),
            _("Live greenhouse telemetry, alerts, and zone trends for the active fleet group."),
            icon="dashboard",
            meta=_("Operations"),
        )
        content_area = ui.column().classes("w-full gap-5")
    selected_gh: dict[str, Any] = {"id": None}

    async def load_data() -> None:
        """Fetch telemetry data and render dashboard content."""
        content_area.clear()

        try:
            async with api_client(timeout=10.0) as client:
                groups_resp = await client.get("/api/groups")
                groups_resp.raise_for_status()
                groups = groups_resp.json()
                if not groups:
                    with content_area:
                        empty_state(
                            _("No greenhouse groups available"),
                            _("Create a group or start the simulator after switching to Internal simulator mode."),
                            icon="groups",
                        )
                    return
                group_id = str(groups[0].get("id"))
                latest_data: dict[str, Any] = {"readings": []}
                for group in groups:
                    candidate_group_id = str(group.get("id"))
                    latest_resp = await client.get(f"/api/groups/{candidate_group_id}/telemetry/latest")
                    latest_resp.raise_for_status()
                    candidate_latest_data = latest_resp.json()
                    if candidate_latest_data.get("readings"):
                        group_id = candidate_group_id
                        latest_data = candidate_latest_data
                        break

                anomalies_resp = await client.get(f"/api/groups/{group_id}/telemetry/anomalies")
                anomalies_resp.raise_for_status()
                anomalies_data = anomalies_resp.json()

        except httpx.HTTPError as exc:
            with content_area:
                empty_state(
                    _("Error loading data"),
                    _("Make sure the API is running and InfluxDB is available. Details: {error}", error=exc),
                    icon="cloud_off",
                )
            return

        readings = latest_data.get("readings", [])
        anomalies = anomalies_data.get("anomalies", [])

        if not readings:
            with content_area:
                empty_state(
                    _("No telemetry data available"),
                    _("Start the simulator to generate data and see the fleet cockpit come alive."),
                    icon="sensors_off",
                )
            return

        # Transform data
        greenhouses = transform_latest_to_greenhouses(readings)
        group_data = build_group_data(greenhouses, anomalies, group_id)

        # --- Group overview ---
        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("w-2/3 min-w-[320px]"):
                group_overview_card(group_data)

            with ui.column().classes("w-1/3 min-w-[280px]"):
                alert_panel(anomalies)

        # --- Greenhouse cards ---
        with section_card(_("Greenhouses"), _("Select a house to inspect zone-level metrics and trends."), icon="warehouse"):
            greenhouse_grid = ui.row().classes("w-full gap-4 flex-wrap mt-4")
        with greenhouse_grid:
            for gh_id, gh_data in greenhouses.items():
                def view_zones_handler(gh: str):
                    async def handler() -> None:
                        await select_greenhouse(gh)

                    return handler

                column = ui.column().classes("w-64 cursor-pointer")
                with column:
                    greenhouse_card(gh_data)
                    ui.button(
                        _("View zones"),
                        on_click=view_zones_handler(gh_id),
                    ).props("flat color=primary size=sm").classes("mt-2")

        # --- Zone detail area (hidden initially) ---
        zone_detail_container = ui.column().classes("w-full gap-4 mt-4")
        zone_detail_container.set_visibility(False)

        async def select_greenhouse(gh_id: str) -> None:
            """Show zone detail for a selected greenhouse."""
            selected_gh["id"] = gh_id
            zone_detail_container.clear()
            zone_detail_container.set_visibility(True)

            with zone_detail_container:
                with section_card(
                    _("Greenhouse: {greenhouse_id}", greenhouse_id=gh_id),
                    _("Zone detail cards and recent six-hour telemetry trends."),
                    icon="yard",
                ):
                    zones = transform_latest_to_zones(readings, gh_id)

                    if not zones:
                        empty_state(_("No zone data available"), _("This greenhouse has not reported zone telemetry yet."), icon="grid_off")
                        return

                    with ui.row().classes("w-full gap-4 flex-wrap mt-4"):
                        for zone in zones:
                            with ui.column().classes("w-72 min-w-[260px]"):
                                zone_detail_card(zone)

                    ui.separator().classes("w-full mt-4")
                    ui.label(_("Zone Charts")).classes("text-lg font-bold mt-3")

            try:
                async with api_client(timeout=10.0) as client:
                    now = datetime.now(timezone.utc)
                    start = (now - timedelta(hours=6)).isoformat()
                    end = now.isoformat()

                    range_resp = await client.get(
                        f"/api/groups/{group_id}/telemetry/range",
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
                        empty_state(_("No historical data for charts"), _("Recent range data will appear here after telemetry accumulates."), icon="show_chart")

            except httpx.HTTPError as exc:
                empty_state(_("Error loading chart data"), str(exc), icon="sync_problem")

    # Initial load
    await load_data()
