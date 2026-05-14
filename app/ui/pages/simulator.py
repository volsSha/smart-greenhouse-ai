"""Simulator control page for the Smart Greenhouse system.

Provides controls for starting/stopping the telemetry simulator,
selecting scenarios, configuring simulation parameters, and a mode
selector to switch between Internal Simulator and Wokwi/MQTT mode.
When the internal simulator is running, a live zone visualization
with animated actuator feedback is shown.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx
from nicegui import ui

from app.i18n.core import _
from app.ui.api_client import api_client, response_error
from app.ui.components.mqtt_status_panel import MQTTStatusPanel
from app.ui.components.zone_visualization import ZoneVisualization
from app.ui.layouts.main_layout import main_layout

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scenario presets
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, dict[str, Any]] = {
    "normal": {
        "label": "Normal",
        "description": "Stable conditions within optimal ranges",
        "icon": "check_circle",
        "color": "#4caf50",
    },
    "dry_soil": {
        "label": "Dry Soil",
        "description": "Low soil moisture across all zones",
        "icon": "water_drop",
        "color": "#ff9800",
    },
    "overheating": {
        "label": "Overheating",
        "description": "Rising temperatures above safe thresholds",
        "icon": "thermostat",
        "color": "#f44336",
    },
    "low_light": {
        "label": "Low Light",
        "description": "Insufficient light levels for photosynthesis",
        "icon": "light_mode",
        "color": "#9e9e9e",
    },
    "sensor_fault": {
        "label": "Sensor Fault",
        "description": "Erratic readings from one or more sensors",
        "icon": "error_outline",
        "color": "#e91e63",
    },
}


def _scenario_label(scenario_key: str) -> str:
    labels = {
        "normal": _("Normal"),
        "dry_soil": _("Dry Soil"),
        "overheating": _("Overheating"),
        "low_light": _("Low Light"),
        "sensor_fault": _("Sensor Fault"),
    }
    return labels.get(scenario_key, scenario_key)


def _scenario_description(scenario_key: str) -> str:
    descriptions = {
        "normal": _("Stable conditions within optimal ranges"),
        "dry_soil": _("Low soil moisture across all zones"),
        "overheating": _("Rising temperatures above safe thresholds"),
        "low_light": _("Insufficient light levels for photosynthesis"),
        "sensor_fault": _("Erratic readings from one or more sensors"),
    }
    return descriptions.get(scenario_key, "")


# ---------------------------------------------------------------------------
# Animations CSS — inject once via shared CSS
# ---------------------------------------------------------------------------

def _load_animations_css() -> None:
    css_path = Path(__file__).parents[2] / "ui" / "static" / "animations.css"
    try:
        css = css_path.read_text()
        ui.add_css(css, shared=True)
    except FileNotFoundError:
        logger.warning("animations.css not found at %s", css_path)


# ---------------------------------------------------------------------------
# Simulator page
# ---------------------------------------------------------------------------


@ui.page("/simulator")
async def simulator() -> None:
    """Render the simulator control page."""
    main_layout()

    ui.label(_("Simulator")).classes("text-2xl font-bold mt-6")
    ui.label(
        _("Control the telemetry data simulator for testing and demos.")
    ).classes("text-sm opacity-70 mt-1")

    # State
    state: dict[str, Any] = {
        "running": False,
        "scenario": "normal",
        "messages_published": 0,
        "last_publish": None,
        "mode": "simulator",
    }

    # Load animations CSS
    _load_animations_css()

    # --- Status indicator ---
    with ui.card().classes("w-full mt-4"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label(_("Status")).classes("text-lg font-bold")
            status_badge = ui.badge(_("Stopped"), color="grey")

        with ui.row().classes("items-center gap-6 mt-2"):
            ui.label(_("Messages published:")).classes("text-sm opacity-70")
            msg_count_label = ui.label("0").classes("text-sm font-mono font-bold")
            ui.separator().props("vertical")
            ui.label(_("Last publish:")).classes("text-sm opacity-70")
            last_publish_label = ui.label("--").classes("text-sm font-mono")

    # --- Active scenario ---
    with ui.card().classes("w-full mt-4"):
        ui.label(_("Active Scenario")).classes("text-lg font-bold")
        active_scenario_label = ui.label(_("Normal")).classes(
            "text-md mt-1 font-semibold"
        ).style("color: #4caf50")
        scenario_desc = ui.label(
            _("Stable conditions within optimal ranges")
        ).classes("text-sm opacity-60 mt-1")

    # --- Scenario selection ---
    with ui.card().classes("w-full mt-4"):
        ui.label(_("Select Scenario")).classes("text-lg font-bold")

        with ui.row().classes("w-full gap-3 mt-3 flex-wrap"):
            for key, scenario in SCENARIOS.items():
                btn = ui.button(
                    _scenario_label(key),
                    icon=scenario["icon"],
                    on_click=lambda k=key: select_scenario(k),
                )
                btn.props(f'color="{scenario["color"]}" outline')

    # --- Configuration ---
    with ui.card().classes("w-full mt-4"):
        ui.label(_("Configuration")).classes("text-lg font-bold")

        with ui.row().classes("w-full gap-4 mt-3"):
            groups_input = ui.number(
                _("Groups"), value=1, min=1, max=10
            ).classes("w-32")

            greenhouses_input = ui.number(
                _("Greenhouses per Group"), value=3, min=1, max=20
            ).classes("w-48")

            zones_input = ui.number(
                _("Zones per Greenhouse"), value=4, min=1, max=20
            ).classes("w-48")

            interval_input = ui.number(
                _("Interval (seconds)"), value=5, min=1, max=300
            ).classes("w-48")

    # --- Mode selector ---
    with ui.card().classes("w-full mt-4"):
        ui.label(_("Operational Mode")).classes("text-lg font-bold")

        with ui.row().classes("items-center gap-4 mt-3"):
            ui.select(
                label=_("Mode"),
                options={
                    "simulator": _("Internal Simulator"),
                    "mqtt": _("Wokwi / MQTT"),
                },
                value=state["mode"],
                on_change=lambda e: _on_mode_change(e.value),
            ).classes("w-64")

            mode_notice = ui.label("").classes("text-sm italic opacity-60")

    # --- Zone visualization ---
    with ui.card().classes("w-full mt-4"):
        ui.label(_("Zone Visualization")).classes("text-lg font-bold")
        with ui.column().classes("w-full gap-4 mt-2") as viz_container:
            viz = ZoneVisualization()
            viz.build(viz_container)
            no_data_label = ui.label(
                _("Start the simulator to see zone data.")
            ).classes("text-sm italic opacity-50")
            mqtt_placeholder = ui.column().classes("w-full gap-2").style("display: none")
            with mqtt_placeholder:
                mqtt_panel = MQTTStatusPanel()
                mqtt_panel.render()

    # --- Result display ---
    result_label = ui.label("").classes("text-sm mt-4")

    # -----------------------------------------------------------------------
    # Timer for zone state polling (active only while simulator runs)
    # -----------------------------------------------------------------------

    async def _refresh_zones() -> None:
        """Poll /api/simulator/zones and update the visualization."""
        if not state["running"] or state["mode"] != "simulator":
            return
        try:
            async with api_client(timeout=5.0) as client:
                resp = await client.get("/api/simulator/zones")
                if resp.status_code == 200:
                    zones = resp.json()
                    if zones:
                        no_data_label.style("display: none")
                        viz.update_all(zones)
                    else:
                        viz.clear()
                        no_data_label.style("display: block")
                else:
                    viz.mark_stopped()
        except httpx.HTTPError:
            logger.debug("Zone state poll failed (simulator may be stopping)")

    zone_timer = ui.timer(
        2.0, _refresh_zones, active=False
    )

    async def _refresh_mqtt_status() -> None:
        if state["mode"] != "mqtt":
            return
        try:
            async with api_client(timeout=5.0) as client:
                resp = await client.get("/api/mqtt/status")
                if resp.status_code == 200:
                    mqtt_panel.update(resp.json())
        except httpx.HTTPError:
            logger.debug("MQTT status poll failed")

    mqtt_timer = ui.timer(
        3.0, _refresh_mqtt_status, active=False
    )

    # -----------------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------------

    def _on_mode_change(new_mode: str) -> None:
        state["mode"] = new_mode
        if new_mode == "simulator":
            mqtt_timer.deactivate()
            mqtt_placeholder.style("display: none")
            no_data_label.style("display: block" if not state["running"] else "none")
            mode_notice.set_text("")
            if state["running"]:
                zone_timer.activate()
        else:
            zone_timer.deactivate()
            mqtt_timer.activate()
            viz.clear()
            no_data_label.style("display: none")
            mqtt_placeholder.style("display: block")
            mode_notice.set_text(_("Run ngrok TCP for local Mosquitto, then use firmware/wokwi-greenhouse-zone/main.py and config.py in hosted Wokwi."))

    def select_scenario(scenario_key: str) -> None:
        """Update the active scenario display."""
        scenario = SCENARIOS[scenario_key]
        state["scenario"] = scenario_key

        active_scenario_label.set_text(_scenario_label(scenario_key))
        active_scenario_label.style(f"color: {scenario['color']}")
        scenario_desc.set_text(_scenario_description(scenario_key))

        ui.notify(
            _("Scenario changed to {scenario}", scenario=_scenario_label(scenario_key)),
            type="info",
        )

    async def start_simulator() -> None:
        """Attempt to start the simulator via the API."""
        config = {
            "scenario": state["scenario"],
            "groups": int(groups_input.value),
            "greenhouses_per_group": int(greenhouses_input.value),
            "zones_per_greenhouse": int(zones_input.value),
            "interval_seconds": int(interval_input.value),
        }

        try:
            async with api_client(timeout=10.0) as client:
                resp = await client.post("/api/simulator/start", json=config)
                resp.raise_for_status()
                result = resp.json()

            state["running"] = True
            state["messages_published"] = result.get("messages_published", 0)
            state["last_publish"] = result.get("last_publish")

            _update_status()
            if state["mode"] == "simulator":
                zone_timer.activate()
                no_data_label.style("display: block")
            result_label.set_text(_("Simulator started successfully"))
            result_label.style("color: #4caf50")
            ui.notify(_("Simulator started"), type="positive")

        except httpx.HTTPError as exc:
            state["running"] = False
            _update_status()
            detail = response_error(exc.response) if isinstance(exc, httpx.HTTPStatusError) else str(exc)
            result_label.set_text(_("Failed to start: {detail}", detail=detail))
            result_label.style("color: #f44336")
            ui.notify(_("Failed to start simulator"), type="negative")

    async def stop_simulator() -> None:
        """Attempt to stop the simulator via the API."""
        try:
            async with api_client(timeout=10.0) as client:
                resp = await client.post("/api/simulator/stop")
                resp.raise_for_status()
                result = resp.json()

            state["running"] = False
            state["messages_published"] = result.get("messages_published", state["messages_published"])

            zone_timer.deactivate()
            if state["mode"] == "simulator":
                viz.mark_stopped()
            _update_status()
            result_label.set_text(_("Simulator stopped"))
            result_label.style("color: #ff9800")
            ui.notify(_("Simulator stopped"), type="warning")

        except httpx.HTTPError as exc:
            detail = response_error(exc.response) if isinstance(exc, httpx.HTTPStatusError) else str(exc)
            result_label.set_text(_("Failed to stop: {detail}", detail=detail))
            result_label.style("color: #f44336")
            ui.notify(_("Failed to stop simulator"), type="negative")

    def _update_status() -> None:
        """Refresh the status display to match current state."""
        if state["running"]:
            status_badge.set_text(_("Running"))
            status_badge._props["color"] = "positive"
            status_badge.update()
            start_btn.props("disable")
            stop_btn.props(remove="disable")
        else:
            status_badge.set_text(_("Stopped"))
            status_badge._props["color"] = "grey"
            status_badge.update()
            start_btn.props(remove="disable")
            stop_btn.props("disable")

        msg_count_label.set_text(str(state["messages_published"]))
        if state["last_publish"]:
            last_publish_label.set_text(str(state["last_publish"])[:19])
        else:
            last_publish_label.set_text("--")

    # --- Control buttons ---
    with ui.row().classes("w-full gap-4 mt-6"):
        start_btn = ui.button(
            _("Start Simulator"),
            icon="play_arrow",
            color="positive",
            on_click=start_simulator,
        ).classes("px-6")

        stop_btn = ui.button(
            _("Stop Simulator"),
            icon="stop",
            color="negative",
            on_click=stop_simulator,
        ).props("disable")
