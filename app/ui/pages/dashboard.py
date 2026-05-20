"""Dashboard page -- fleet overview with real-time telemetry display.

Renders group overview cards, greenhouse detail views with zone charts,
and an alert panel. Handles loading, empty, and error states explicitly.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

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

ChartSize = Literal["compact", "normal", "expanded"]

_RANGE_PRESETS: dict[str, timedelta] = {
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "3d": timedelta(days=3),
    "7d": timedelta(days=7),
}

_RANGE_LABELS: dict[str, str] = {
    "30m": "30 min",
    "1h": "1 h",
    "6h": "6 h",
    "24h": "24 h",
    "3d": "3 d",
    "7d": "7 d",
    "custom": "Custom",
}

_CHART_SIZE_LABELS: dict[ChartSize, str] = {
    "compact": "Compact",
    "normal": "Normal",
    "expanded": "Expanded",
}


def time_range_bounds(preset: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    end = now or datetime.now(timezone.utc)
    return end - _RANGE_PRESETS.get(preset, _RANGE_PRESETS["6h"]), end


def range_query_limit(start: datetime, end: datetime) -> int:
    seconds = max((end - start).total_seconds(), 0)
    if seconds <= 6 * 60 * 60:
        return 1000
    if seconds <= 24 * 60 * 60:
        return 3000
    return 10000


def format_datetime_input(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")


def parse_datetime_input(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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


def alert_identity(alert: dict[str, Any]) -> str:
    if alert.get("id"):
        return str(alert["id"])
    return "|".join(
        str(alert.get(key, ""))
        for key in ("_time", "greenhouse_id", "zone_id", "metric", "_value", "severity")
    )


def normalize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(alert)
    if "timestamp" not in normalized and normalized.get("created_at"):
        normalized["timestamp"] = normalized["created_at"]
    return normalized


def build_group_data(
    greenhouses: dict[str, dict[str, Any]],
    active_alerts: list[dict[str, Any]],
    group_id: str,
) -> dict[str, Any]:
    """Build group overview data from greenhouse and active alert data."""
    return {
        "group_id": group_id,
        "name": group_id,
        "greenhouse_count": len(greenhouses),
        "active_alerts": len(active_alerts),
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
    dashboard_state: dict[str, Any] = {
        "range_preset": "6h",
        "custom_start": None,
        "custom_end": None,
        "chart_size": "normal",
        "paused": False,
        "last_updated": None,
        "dismissing_alerts": set(),
    }
    load_lock = asyncio.Lock()

    def translated_range_options() -> dict[str, str]:
        return {
            "30m": _("30 min"),
            "1h": _("1 h"),
            "6h": _("6 h"),
            "24h": _("24 h"),
            "3d": _("3 d"),
            "7d": _("7 d"),
            "custom": _("Custom"),
        }

    def range_code_from_label(label: str) -> str:
        for code, translated_label in translated_range_options().items():
            if label == translated_label:
                return code
        for code, raw_label in _RANGE_LABELS.items():
            if label == raw_label:
                return code
        return "6h"

    def translated_chart_size_options() -> dict[ChartSize, str]:
        return {
            "compact": _("Compact"),
            "normal": _("Normal"),
            "expanded": _("Expanded"),
        }

    def chart_size_code_from_label(label: str) -> ChartSize:
        for code, translated_label in translated_chart_size_options().items():
            if label == translated_label:
                return code
        for code, raw_label in _CHART_SIZE_LABELS.items():
            if label == raw_label:
                return code
        return "normal"

    def current_range_bounds() -> tuple[datetime, datetime]:
        if dashboard_state["range_preset"] == "custom":
            start = parse_datetime_input(str(dashboard_state.get("custom_start") or ""))
            end = parse_datetime_input(str(dashboard_state.get("custom_end") or ""))
            if start and end and start < end:
                return start, end
        return time_range_bounds(str(dashboard_state["range_preset"]))

    async def load_data() -> None:
        if load_lock.locked():
            return

        async with load_lock:
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
    
                    alerts_resp = await client.get(
                        f"/api/groups/{group_id}/alerts",
                        params={"status": "active"},
                    )
                    alerts_resp.raise_for_status()
                    alerts_data = alerts_resp.json()

            except httpx.HTTPError as exc:
                with content_area:
                    empty_state(
                        _("Error loading data"),
                        _("Make sure the API is running and InfluxDB is available. Details: {error}", error=exc),
                        icon="cloud_off",
                    )
                return
    
            readings = latest_data.get("readings", [])
            alerts = [normalize_alert(alert) for alert in alerts_data]

            dashboard_state["last_updated"] = datetime.now(timezone.utc)
    
            content_area.clear()
            refresh_timer.deactivate()

            if not readings:
                with content_area:
                    empty_state(
                        _("No telemetry data available"),
                        _("Start the simulator to generate data and see the fleet cockpit come alive."),
                        icon="sensors_off",
                    )
                return
            with content_area:
                greenhouses = transform_latest_to_greenhouses(readings)
                group_data = build_group_data(greenhouses, alerts, group_id)
        
                async def refresh_dashboard() -> None:
                    await load_data()
        
                async def toggle_pause() -> None:
                    dashboard_state["paused"] = not dashboard_state["paused"]
                    await load_data()

                async def dismiss_alert(alert: dict[str, Any]) -> None:
                    alert_id = alert.get("id")
                    if not alert_id:
                        ui.notify(_("Unable to dismiss alert"), type="negative")
                        return
                    dismissing_alerts = dashboard_state["dismissing_alerts"]
                    if alert_id in dismissing_alerts:
                        return
                    dismissing_alerts.add(alert_id)
                    try:
                        async with api_client(timeout=10.0) as client:
                            response = await client.patch(
                                f"/api/groups/{group_id}/alerts/{alert_id}",
                                json={"status": "dismissed"},
                            )
                            response.raise_for_status()
                        ui.notify(_("Alert dismissed"), type="positive")
                    except httpx.HTTPError:
                        ui.notify(_("Unable to dismiss alert"), type="negative")
                    finally:
                        dismissing_alerts.discard(alert_id)
                        await load_data()

                async def dismiss_all_alerts() -> None:
                    alert_ids = [alert.get("id") for alert in alerts if alert.get("id")]
                    if not alert_ids:
                        ui.notify(_("Unable to dismiss alerts"), type="negative")
                        return

                    failures = 0
                    dismissing_alerts = dashboard_state["dismissing_alerts"]
                    dismissing_alerts.update(alert_ids)
                    try:
                        async with api_client(timeout=10.0) as client:
                            for alert_id in alert_ids:
                                try:
                                    response = await client.patch(
                                        f"/api/groups/{group_id}/alerts/{alert_id}",
                                        json={"status": "dismissed"},
                                    )
                                    response.raise_for_status()
                                except httpx.HTTPError:
                                    failures += 1
                        if failures:
                            ui.notify(_("Some alerts could not be dismissed"), type="warning")
                        else:
                            ui.notify(_("All alerts dismissed"), type="positive")
                    finally:
                        dismissing_alerts.difference_update(alert_ids)
                        await load_data()

                last_updated = dashboard_state.get("last_updated")
                if last_updated:
                    seconds_ago = max(int((datetime.now(timezone.utc) - last_updated).total_seconds()), 0)
                    freshness = _("Last updated {seconds} seconds ago", seconds=seconds_ago)
                else:
                    freshness = _("Last updated just now")
        
                with section_card(_("Dashboard controls"), _("Refresh live data or pause the dashboard during investigation."), icon="tune"):
                    with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                        ui.badge(freshness).props("color=green")
                        ui.button(_("Refresh now"), on_click=refresh_dashboard).props("outline color=primary icon=refresh")
                        pause_label = _("Resume live refresh") if dashboard_state["paused"] else _("Pause live refresh")
                        pause_icon = "play_arrow" if dashboard_state["paused"] else "pause"
                        ui.button(pause_label, on_click=toggle_pause).props(f"outline color=primary icon={pause_icon}")
        
                # --- Group overview ---
                with ui.row().classes("w-full gap-4"):
                    with ui.column().classes("w-2/3 min-w-[320px]"):
                        group_overview_card(group_data)
        
                    with ui.column().classes("w-1/3 min-w-[280px]"):
                        alert_panel(alerts, dismiss_alert, dismiss_all_alerts)
        
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
                        column.on("click", view_zones_handler(gh_id))
                        with column:
                            greenhouse_card(gh_data)
                            ui.button(
                                _("View zones"),
                                on_click=view_zones_handler(gh_id),
                            ).props("flat color=primary size=sm").classes("mt-2")
        
                # --- Zone detail area (hidden initially) ---
                zone_detail_container = ui.column().classes("w-full gap-4 mt-4")
                zone_detail_container.set_visibility(False)
        
                async def render_selected_greenhouse() -> None:
                    if selected_gh["id"]:
                        await select_greenhouse(str(selected_gh["id"]))
        
                async def select_greenhouse(gh_id: str) -> None:
                    selected_gh["id"] = gh_id
                    zone_detail_container.clear()
                    zone_detail_container.set_visibility(True)
        
                    start_dt, end_dt = current_range_bounds()
                    dashboard_state["custom_start"] = dashboard_state.get("custom_start") or format_datetime_input(start_dt)
                    dashboard_state["custom_end"] = dashboard_state.get("custom_end") or format_datetime_input(end_dt)
        
                    async def update_range(event: Any) -> None:
                        dashboard_state["range_preset"] = range_code_from_label(str(event.value))
                        await select_greenhouse(gh_id)
        
                    async def update_chart_size(event: Any) -> None:
                        dashboard_state["chart_size"] = chart_size_code_from_label(str(event.value))
                        await select_greenhouse(gh_id)
        
                    async def update_custom_range() -> None:
                        dashboard_state["range_preset"] = "custom"
                        await select_greenhouse(gh_id)
        
                    with zone_detail_container:
                        with section_card(
                            _("Greenhouse: {greenhouse_id}", greenhouse_id=gh_id),
                            _("Zone detail cards and telemetry trends for the selected time range."),
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
                            with ui.row().classes("w-full items-end gap-3 flex-wrap"):
                                range_options = translated_range_options()
                                ui.select(
                                    list(range_options.values()),
                                    label=_("Time range"),
                                    value=range_options.get(str(dashboard_state["range_preset"]), range_options["6h"]),
                                    on_change=update_range,
                                ).props("outlined dense").classes("min-w-36")
                                custom_start = ui.input(
                                    _("Start"),
                                    value=str(dashboard_state["custom_start"]),
                                    on_change=lambda event: dashboard_state.update(custom_start=event.value),
                                ).props("outlined dense type=datetime-local").classes("min-w-52")
                                custom_end = ui.input(
                                    _("End"),
                                    value=str(dashboard_state["custom_end"]),
                                    on_change=lambda event: dashboard_state.update(custom_end=event.value),
                                ).props("outlined dense type=datetime-local").classes("min-w-52")
                                ui.button(_("Apply custom range"), on_click=update_custom_range).props("outline color=primary")
                                size_options = translated_chart_size_options()
                                ui.select(
                                    list(size_options.values()),
                                    label=_("Chart size"),
                                    value=size_options.get(dashboard_state["chart_size"], size_options["normal"]),
                                    on_change=update_chart_size,
                                ).props("outlined dense").classes("min-w-36")
                                custom_inputs_visible = dashboard_state["range_preset"] == "custom"
                                custom_start.set_visibility(custom_inputs_visible)
                                custom_end.set_visibility(custom_inputs_visible)
        
                    try:
                        async with api_client(timeout=10.0) as client:
                            start_dt, end_dt = current_range_bounds()
                            range_resp = await client.get(
                                f"/api/groups/{group_id}/telemetry/range",
                                params={
                                    "start": start_dt.isoformat(),
                                    "end": end_dt.isoformat(),
                                    "greenhouse_id": gh_id,
                                    "limit": range_query_limit(start_dt, end_dt),
                                },
                            )
                            range_resp.raise_for_status()
                            range_data = range_resp.json()
                            range_readings = range_data.get("readings", [])
        
                            if range_readings:
                                temp_readings = [
                                    r for r in range_readings if r.get("metric") == "temperature"
                                ]
                                humidity_readings = [
                                    r for r in range_readings if r.get("metric") == "air_humidity"
                                ]
                                soil_readings = [
                                    r for r in range_readings if r.get("metric") == "soil_moisture"
                                ]
                                chart_size = dashboard_state["chart_size"]
        
                                with ui.row().classes("w-full gap-4 flex-wrap"):
                                    if temp_readings:
                                        with ui.column().classes("grow basis-[320px] min-w-[300px]"):
                                            temperature_chart(temp_readings, chart_size)
                                    if humidity_readings:
                                        with ui.column().classes("grow basis-[320px] min-w-[300px]"):
                                            humidity_chart(humidity_readings, chart_size)
                                    if soil_readings:
                                        with ui.column().classes("grow basis-[320px] min-w-[300px]"):
                                            soil_moisture_chart(soil_readings, chart_size)
        
                                with ui.row().classes("w-full mt-4"):
                                    multi_metric_chart(range_readings, size=chart_size)
                            else:
                                empty_state(_("No historical data for charts"), _("Range data will appear here after telemetry accumulates."), icon="show_chart")
        
                    except httpx.HTTPError as exc:
                        empty_state(_("Error loading chart data"), str(exc), icon="sync_problem")
        
                if selected_gh["id"]:
                    await render_selected_greenhouse()
                if not dashboard_state["paused"]:
                    refresh_timer.activate()

    async def refresh_if_live() -> None:
        if not dashboard_state["paused"]:
            await load_data()

    refresh_timer = ui.timer(10.0, refresh_if_live, active=False)

    # Initial load
    await load_data()
    refresh_timer.activate()
