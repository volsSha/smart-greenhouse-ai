"""Interactive greenhouse zone visualization with animated actuator feedback.

Renders zone cards with metric badges and actuator indicators. Metrics
update via ``set_text()`` on individual labels. Actuator animation states
toggle CSS keyframe classes so running animations are never interrupted
by DOM replacement.
"""

from __future__ import annotations

from typing import Any

from nicegui import ui

from app.ui.components.telemetry_cards import METRIC_THRESHOLDS

# ---------------------------------------------------------------------------
# Actuator metadata
# ---------------------------------------------------------------------------

ACTUATOR_CONFIG: dict[str, dict[str, Any]] = {
    "pump": {"icon": "water_drop", "label": "Pump"},
    "fan": {"icon": "toys", "label": "Fan"},
    "heater": {"icon": "whatshot", "label": "Heater"},
    "lamp": {"icon": "lightbulb", "label": "Lamp"},
}

# ---------------------------------------------------------------------------
# Threshold helpers
# ---------------------------------------------------------------------------

_STATUS_COLORS: dict[str, str] = {
    "green": "#4caf50",
    "yellow": "#ff9800",
    "red": "#f44336",
}


def _metric_status(metric: str, value: float) -> str:
    thresholds = METRIC_THRESHOLDS.get(metric)
    if thresholds is None:
        return "green"
    g = thresholds.get("green", (0, 100))
    y = thresholds.get("yellow", (0, 100))
    if g[0] <= value <= g[1]:
        return "green"
    if y[0] <= value <= y[1]:
        return "yellow"
    return "red"


METRIC_UNITS: dict[str, tuple[str, str]] = {
    "temperature": ("Temperature", "°C"),
    "air_humidity": ("Humidity", "%"),
    "soil_moisture": ("Soil Moisture", "%"),
    "co2": ("CO₂", "ppm"),
    "light": ("Light", "lux"),
}


# ---------------------------------------------------------------------------
# Zone Card (internal helper)
# ---------------------------------------------------------------------------


class _ZoneCard:
    """One card showing a single zone's metrics and actuators."""

    def __init__(self, zone_data: dict[str, Any]) -> None:
        self.zone_id: str = zone_data.get("zone_id", "")
        self._metrics: dict[str, ui.label] = {}
        self._actuators: dict[str, ui.icon] = {}

        with ui.card().classes("w-full zone-card").props("flat bordered") as self._card:
            # --- Header ---
            with ui.row().classes("items-center justify-between w-full"):
                ui.label(self.zone_id).classes("text-md font-bold")
                self._status_dot = ui.icon("circle", size="0.6rem").style("color: #4caf50")

            # --- Metrics grid ---
            with ui.grid(columns=3).classes("w-full gap-x-6 gap-y-1 mt-2"):
                for metric_key, (label, unit) in METRIC_UNITS.items():
                    value = zone_data.get(metric_key, 0.0)
                    status = _metric_status(metric_key, value)
                    color = _STATUS_COLORS.get(status, "#9e9e9e")

                    with ui.row().classes("items-center gap-1 zone-metric"):
                        ui.label(f"{label}:").classes("text-xs opacity-70")
                        lbl = ui.label(f"{value:.1f} {unit}").classes(
                            "text-xs font-semibold zone-metric-value"
                        ).style(f"color: {color}")
                        self._metrics[metric_key] = lbl

            # --- Actuator indicators ---
            ui.separator().classes("my-2")
            with ui.row().classes("items-center gap-4"):
                for act_key, cfg in ACTUATOR_CONFIG.items():
                    act_data = zone_data.get("actuators", {}).get(act_key, {"active": False})
                    icon = ui.icon(cfg["icon"], size="1.4rem").classes(
                        f"actuator-{act_key} {'active' if act_data.get('active') else ''}"
                    )
                    tooltip = f"{cfg['label']}: {'ON' if act_data.get('active') else 'OFF'}"
                    icon.tooltip(tooltip)
                    self._actuators[act_key] = icon

    # ------------------------------------------------------------------
    # Updates
    # ------------------------------------------------------------------

    def update_metrics(self, zone_data: dict[str, Any]) -> None:
        """Update metric values and status colours in place."""
        for metric_key, (label, unit) in METRIC_UNITS.items():
            value = zone_data.get(metric_key, 0.0)
            status = _metric_status(metric_key, value)
            color = _STATUS_COLORS.get(status, "#9e9e9e")
            lbl = self._metrics.get(metric_key)
            if lbl is not None:
                lbl.set_text(f"{value:.1f} {unit}")
                lbl.style(f"color: {color}")

    def update_actuators(self, zone_data: dict[str, Any]) -> None:
        """Toggle actuator animation classes based on active state."""
        actuators_data = zone_data.get("actuators", {})
        for act_key, icon in self._actuators.items():
            act = actuators_data.get(act_key, {"active": False})
            is_active = act.get("active", False)
            icon.classes(remove="active")
            if is_active:
                icon.classes(add="active")
            icon.tooltip(
                f"{ACTUATOR_CONFIG[act_key]['label']}: {'ON' if is_active else 'OFF'}"
            )

    def set_stopped(self, stopped: bool) -> None:
        """Mark the card as stopped (greyed out)."""
        self._card.classes(remove="stopped")
        if stopped:
            self._card.classes(add="stopped")
            self._status_dot.style("color: #9e9e9e")
        else:
            self._status_dot.style("color: #4caf50")


# ---------------------------------------------------------------------------
# ZoneVisualization component
# ---------------------------------------------------------------------------


class ZoneVisualization:
    """Container component that manages a set of ``_ZoneCard`` instances.

    Usage inside a page::

        viz = ZoneVisualization()
        with ui.column() as container:
            viz.build(container)

        # On timer tick:
        zone_data = await fetch_zones()
        viz.update_all(zone_data)
    """

    def __init__(self) -> None:
        self._container: ui.column | None = None
        self._zone_cards: dict[str, _ZoneCard] = {}

    def build(self, container: ui.column) -> None:
        """Attach to an existing column element as the parent container."""
        self._container = container

    def update_all(self, zones_data: list[dict[str, Any]]) -> None:
        """Rebuild or update zone cards from a list of zone dicts.

        New zones get fresh cards; existing zones get metrics/actuators
        updated in place. Removed zones are cleared.
        """
        if self._container is None:
            return

        incoming_ids = {z.get("zone_id") for z in zones_data}
        current_ids = set(self._zone_cards)

        # Remove stale cards
        for zid in current_ids - incoming_ids:
            card = self._zone_cards.pop(zid)
            card._card.delete()

        # Add / update
        for zdata in zones_data:
            zid = zdata.get("zone_id", "")
            if zid in self._zone_cards:
                card = self._zone_cards[zid]
                card.update_metrics(zdata)
                card.update_actuators(zdata)
                card.set_stopped(False)
            else:
                card = _ZoneCard(zdata)
                self._zone_cards[zid] = card

    def mark_stopped(self) -> None:
        """Grey out all zone cards when the simulator is stopped."""
        for card in self._zone_cards.values():
            card.set_stopped(True)

    def clear(self) -> None:
        """Remove all zone cards."""
        for card in self._zone_cards.values():
            card._card.delete()
        self._zone_cards.clear()
