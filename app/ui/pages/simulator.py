"""Simulator control page for the Smart Greenhouse system.

Provides controls for starting/stopping the telemetry simulator,
selecting scenarios, and configuring simulation parameters.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from nicegui import ui

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


# ---------------------------------------------------------------------------
# Simulator page
# ---------------------------------------------------------------------------


@ui.page("/simulator")
async def simulator() -> None:
    """Render the simulator control page."""
    main_layout()

    ui.label("Simulator").classes("text-2xl font-bold mt-6")
    ui.label(
        "Control the telemetry data simulator for testing and demos."
    ).classes("text-sm opacity-70 mt-1")

    # State
    state: dict[str, Any] = {
        "running": False,
        "scenario": "normal",
        "messages_published": 0,
        "last_publish": None,
    }

    # --- Status indicator ---
    with ui.card().classes("w-full mt-4"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label("Status").classes("text-lg font-bold")
            status_badge = ui.badge("Stopped", color="grey")

        with ui.row().classes("items-center gap-6 mt-2"):
            ui.label("Messages published:").classes("text-sm opacity-70")
            msg_count_label = ui.label("0").classes("text-sm font-mono font-bold")
            ui.separator().props("vertical")
            ui.label("Last publish:").classes("text-sm opacity-70")
            last_publish_label = ui.label("--").classes("text-sm font-mono")

    # --- Active scenario ---
    with ui.card().classes("w-full mt-4"):
        ui.label("Active Scenario").classes("text-lg font-bold")
        active_scenario_label = ui.label("Normal").classes(
            "text-md mt-1 font-semibold"
        ).style("color: #4caf50")
        scenario_desc = ui.label(
            "Stable conditions within optimal ranges"
        ).classes("text-sm opacity-60 mt-1")

    # --- Scenario selection ---
    with ui.card().classes("w-full mt-4"):
        ui.label("Select Scenario").classes("text-lg font-bold")

        with ui.row().classes("w-full gap-3 mt-3 flex-wrap"):
            for key, scenario in SCENARIOS.items():
                btn = ui.button(
                    scenario["label"],
                    icon=scenario["icon"],
                    on_click=lambda k=key: select_scenario(k),
                )
                btn.props(f'color="{scenario["color"]}" outline')

    # --- Configuration ---
    with ui.card().classes("w-full mt-4"):
        ui.label("Configuration").classes("text-lg font-bold")

        with ui.row().classes("w-full gap-4 mt-3"):
            groups_input = ui.number(
                "Groups", value=1, min=1, max=10
            ).classes("w-32")

            greenhouses_input = ui.number(
                "Greenhouses per Group", value=3, min=1, max=20
            ).classes("w-48")

            zones_input = ui.number(
                "Zones per Greenhouse", value=4, min=1, max=20
            ).classes("w-48")

            interval_input = ui.number(
                "Interval (seconds)", value=5, min=1, max=300
            ).classes("w-48")

    # --- Control buttons ---
    with ui.row().classes("w-full gap-4 mt-6"):
        start_btn = ui.button(
            "Start Simulator",
            icon="play_arrow",
            color="positive",
            on_click=start_simulator,
        ).classes("px-6")

        stop_btn = ui.button(
            "Stop Simulator",
            icon="stop",
            color="negative",
            on_click=stop_simulator,
        ).props('disable')

    # --- Result display ---
    result_label = ui.label("").classes("text-sm mt-4")

    # -----------------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------------

    def select_scenario(scenario_key: str) -> None:
        """Update the active scenario display."""
        scenario = SCENARIOS[scenario_key]
        state["scenario"] = scenario_key

        active_scenario_label.set_text(scenario["label"])
        active_scenario_label.style(f"color: {scenario['color']}")
        scenario_desc.set_text(scenario["description"])

        ui.notify(
            f"Scenario changed to {scenario['label']}",
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
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post("/api/simulator/start", json=config)
                resp.raise_for_status()
                result = resp.json()

            state["running"] = True
            state["messages_published"] = result.get("messages_published", 0)
            state["last_publish"] = result.get("last_publish")

            _update_status()
            result_label.set_text("Simulator started successfully")
            result_label.style("color: #4caf50")
            ui.notify("Simulator started", type="positive")

        except httpx.HTTPError as exc:
            state["running"] = False
            _update_status()
            result_label.set_text(f"Failed to start: {exc}")
            result_label.style("color: #f44336")
            ui.notify("Failed to start simulator", type="negative")

    async def stop_simulator() -> None:
        """Attempt to stop the simulator via the API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post("/api/simulator/stop")
                resp.raise_for_status()
                result = resp.json()

            state["running"] = False
            state["messages_published"] = result.get("messages_published", state["messages_published"])

            _update_status()
            result_label.set_text("Simulator stopped")
            result_label.style("color: #ff9800")
            ui.notify("Simulator stopped", type="warning")

        except httpx.HTTPError as exc:
            result_label.set_text(f"Failed to stop: {exc}")
            result_label.style("color: #f44336")
            ui.notify("Failed to stop simulator", type="negative")

    def _update_status() -> None:
        """Refresh the status display to match current state."""
        if state["running"]:
            status_badge.set_text("Running")
            status_badge._props["color"] = "positive"
            status_badge.update()
            start_btn.props("disable")
            stop_btn.props(remove="disable")
        else:
            status_badge.set_text("Stopped")
            status_badge._props["color"] = "grey"
            status_badge.update()
            start_btn.props(remove="disable")
            stop_btn.props("disable")

        msg_count_label.set_text(str(state["messages_published"]))
        if state["last_publish"]:
            last_publish_label.set_text(str(state["last_publish"])[:19])
        else:
            last_publish_label.set_text("--")
