"""Greenhouse map state and rendering helpers for the control page."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from math import ceil, sqrt
from typing import Callable

from nicegui.events import MouseEventArguments

from nicegui import ui

from app.i18n.core import _
from app.ui.components.telemetry_cards import METRIC_THRESHOLDS
from app.ui.components.control_panel_state import ScopeOption


@dataclass(frozen=True)
class MapZone:
    id: str
    label: str
    row: int
    column: int
    x: int
    y: int
    width: int
    height: int
    selected: bool = False
    pending_count: int = 0
    warning: bool = False
    no_data: bool = False
    aria_label: str = ""


@dataclass(frozen=True)
class GreenhouseMapModel:
    zones: list[MapZone]
    columns: int
    width: int = 0
    height: int = 0
    empty: bool = False


def metric_status(metric: str, value: float) -> str:
    thresholds = METRIC_THRESHOLDS.get(metric)
    if thresholds is None:
        return "neutral"
    green = thresholds.get("green", (0, 100))
    yellow = thresholds.get("yellow", (0, 100))
    if green[0] <= value <= green[1]:
        return "neutral"
    if yellow[0] <= value <= yellow[1]:
        return "warning"
    return "critical"


def zone_has_warning(telemetry: dict[str, object]) -> bool:
    for metric, value in telemetry.items():
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if metric_status(metric, numeric) in {"warning", "critical"}:
            return True
    return False


def build_greenhouse_map_model(
    zones: list[ScopeOption],
    *,
    selected_zone_id: str | None = None,
    pending_counts: dict[str, int] | None = None,
    telemetry_by_zone: dict[str, dict[str, object]] | None = None,
) -> GreenhouseMapModel:
    if not zones:
        return GreenhouseMapModel(zones=[], columns=0, empty=True)

    pending_counts = pending_counts or {}
    telemetry_by_zone = telemetry_by_zone or {}
    columns = max(1, ceil(sqrt(len(zones))))
    cell_width = 220
    cell_height = 140
    gap = 18
    rows = ceil(len(zones) / columns)
    width = columns * cell_width + (columns + 1) * gap
    height = rows * cell_height + (rows + 1) * gap
    map_zones: list[MapZone] = []

    for index, zone in enumerate(zones):
        row = index // columns
        column = index % columns
        telemetry = telemetry_by_zone.get(zone.id, {})
        pending_count = pending_counts.get(zone.id, 0)
        selected = zone.id == selected_zone_id
        state_parts = []
        if selected:
            state_parts.append(_("selected"))
        if pending_count:
            state_parts.append(_("{count} pending proposals", count=pending_count))
        if not telemetry:
            state_parts.append(_("no telemetry"))
        aria_suffix = f" ({', '.join(state_parts)})" if state_parts else ""
        map_zones.append(
            MapZone(
                id=zone.id,
                label=zone.label,
                row=row,
                column=column,
                x=gap + column * (cell_width + gap),
                y=gap + row * (cell_height + gap),
                width=cell_width,
                height=cell_height,
                selected=selected,
                pending_count=pending_count,
                warning=zone_has_warning(telemetry),
                no_data=not telemetry,
                aria_label=f"{zone.label}{aria_suffix}",
            )
        )

    return GreenhouseMapModel(zones=map_zones, columns=columns, width=width, height=height)


def zone_at_point(model: GreenhouseMapModel, x: float, y: float) -> MapZone | None:
    for zone in model.zones:
        if zone.x <= x <= zone.x + zone.width and zone.y <= y <= zone.y + zone.height:
            return zone
    return None


def build_greenhouse_svg(model: GreenhouseMapModel) -> str:
    zones_markup = []
    for zone in model.zones:
        classes = ["control-svg-zone"]
        if zone.selected:
            classes.append("selected")
        if zone.pending_count:
            classes.append("pending")
        if zone.warning:
            classes.append("warning")
        if zone.no_data:
            classes.append("no-data")
        label = escape(zone.label)
        aria_label = escape(zone.aria_label, quote=True)
        status = escape(_("No telemetry") if zone.no_data else _("Live context"))
        pending = ""
        if zone.pending_count:
            pending = f'''
            <circle class="control-svg-pending-dot" cx="{zone.x + zone.width - 24}" cy="{zone.y + 24}" r="16" />
            <text class="control-svg-pending-text" x="{zone.x + zone.width - 24}" y="{zone.y + 30}" text-anchor="middle">{zone.pending_count}</text>
            '''
        zones_markup.append(
            f'''
            <g class="{' '.join(classes)}" data-zone-id="{escape(zone.id, quote=True)}" role="button" tabindex="0" aria-label="{aria_label}">
                <rect x="{zone.x}" y="{zone.y}" width="{zone.width}" height="{zone.height}" rx="18" />
                <text class="control-svg-zone-label" x="{zone.x + 18}" y="{zone.y + 42}">{label}</text>
                <text class="control-svg-zone-status" x="{zone.x + 18}" y="{zone.y + 72}">{status}</text>
                {pending}
            </g>
            '''
        )
    return f'''
    <svg class="control-greenhouse-svg" viewBox="0 0 {model.width} {model.height}" role="group" aria-label="{escape(_('Greenhouse zone map'), quote=True)}" xmlns="http://www.w3.org/2000/svg">
        <rect class="control-svg-house" x="4" y="4" width="{max(model.width - 8, 0)}" height="{max(model.height - 8, 0)}" rx="28" />
        {''.join(zones_markup)}
    </svg>
    '''


def render_greenhouse_map(model: GreenhouseMapModel, on_select: Callable[[str], object]) -> None:
    if model.empty:
        with ui.column().classes("control-map-empty items-center justify-center w-full p-8"):
            ui.icon("grid_off", size="2rem").classes("opacity-50")
            ui.label(_("No zones configured")).classes("text-lg font-semibold")
            ui.label(_("Create zones for this greenhouse before using the operator panel.")).classes("text-sm opacity-70")
        return

    def handle_map_click(event: MouseEventArguments) -> None:
        zone = zone_at_point(model, float(event.image_x), float(event.image_y))
        if zone is not None:
            on_select(zone.id)

    ui.interactive_image(
        content=build_greenhouse_svg(model),
        size=(model.width, model.height),
        on_mouse=handle_map_click,
        events=["click"],
        cross=False,
        sanitize=False,
    ).classes("control-greenhouse-map w-full")

    with ui.row().classes("control-map-fallback-list w-full gap-2 mt-3 flex-wrap"):
        for zone in model.zones:
            ui.button(zone.label, on_click=lambda zone_id=zone.id: on_select(zone_id)).props(
                f'dense outline aria-label="{escape(zone.aria_label, quote=True)}"'
            )
