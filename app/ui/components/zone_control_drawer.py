"""Selected-zone drawer rendering for the control operator panel."""

from __future__ import annotations

from typing import Any, Callable

from nicegui import ui

from app.i18n.core import _
from app.ui.components.actuator_controls import render_actuator_controls
from app.ui.components.control_panel_state import ZoneContext
from app.ui.components.design import empty_state, section_card
from app.ui.components.proposed_action_card import proposed_action_card
from app.ui.components.telemetry_cards import _metric_status, metric_badge

_METRIC_UNITS: dict[str, tuple[str, str]] = {
    "temperature": ("Temperature", "C"),
    "air_humidity": ("Humidity", "%"),
    "soil_moisture": ("Soil Moisture", "%"),
    "co2": ("CO2", "ppm"),
    "light": ("Light", "lux"),
}


def command_to_action(command: dict[str, Any], context: ZoneContext | None = None, current_mode: str | None = None) -> dict[str, Any]:
    command_mode = str(command.get("mode") or "mqtt")
    action = {
        "command_id": str(command.get("id", "")),
        "group_id": str(command.get("group_id", "")),
        "greenhouse_id": str(command.get("greenhouse_id", "")),
        "zone_id": str(command.get("zone_id", "")),
        "actuator": command.get("actuator_name") or command.get("actuator") or "unknown",
        "action": command.get("action"),
        "value": command.get("value"),
        "duration_seconds": command.get("duration_seconds"),
        "reason": command.get("reason"),
        "status": command.get("status"),
        "mode": command_mode,
        "mode_mismatch": bool(current_mode and command_mode != current_mode),
        "validation_errors": command.get("validation_errors"),
    }
    if context is not None:
        action["scope_label"] = f"{context.group.label} / {context.greenhouse.label} / {context.zone.label}"
    return action


def render_zone_control_drawer(
    context: ZoneContext | None,
    *,
    on_propose: Callable[[dict[str, object]], object],
    on_approve: Callable[[str], object],
    on_reject: Callable[[str], object],
    control_mode: str | None = None,
    controls_disabled: bool = False,
    disabled_reason: str | None = None,
) -> None:
    if context is None:
        with section_card(_("Selected Zone"), _("Choose a zone from the overview map to inspect and propose changes."), icon="touch_app"):
            empty_state(_("Select a zone"), _("Zone context and proposal controls will appear here."), icon="ads_click")
        return

    with section_card(context.zone.label, f"{context.group.label} / {context.greenhouse.label}", icon="location_on"):
        with ui.column().classes("w-full gap-4 mt-4"):
            _render_telemetry(context)
            _render_plant_context(context)
            _render_pending_commands(context, on_approve=on_approve, on_reject=on_reject, control_mode=control_mode)
            with ui.column().classes("w-full gap-2"):
                ui.label(_("Proposal Controls")).classes("font-semibold")
                if control_mode:
                    ui.badge(_("Mode: {mode}", mode=control_mode.upper()), color="orange" if control_mode == "simulator" else "blue").props("outline")
                ui.label(_("Buttons and sliders create proposals only; approval is still required before execution.")).classes("text-xs opacity-70")
                if disabled_reason:
                    ui.label(disabled_reason).classes("text-xs text-red-600")
                proposal_mode = control_mode if control_mode in {"mqtt", "simulator"} else "mqtt"
        render_actuator_controls(context, on_propose, mode=proposal_mode, disabled=controls_disabled)


def _render_telemetry(context: ZoneContext) -> None:
    with ui.card().classes("greenhouse-card w-full p-3"):
        ui.label(_("Telemetry")).classes("font-semibold")
        if context.telemetry_unavailable:
            ui.label(_("No recent telemetry available for this zone.")).classes("text-xs opacity-60")
            return
        with ui.column().classes("gap-1 mt-2"):
            for metric, (label, unit) in _METRIC_UNITS.items():
                if metric not in context.telemetry:
                    continue
                value = context.telemetry[metric]
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                metric_badge(_(label), numeric, unit, _metric_status(metric, numeric))


def _render_plant_context(context: ZoneContext) -> None:
    with ui.card().classes("greenhouse-card w-full p-3"):
        ui.label(_("Plant Context")).classes("font-semibold")
        if context.plant.primary is None:
            ui.label(_("No plant batch assigned to this zone.")).classes("text-xs opacity-60")
            return
        batch = context.plant.primary
        ui.label(str(batch.get("name") or batch.get("species") or _("Plant batch"))).classes("text-sm font-medium mt-1")
        details = [str(value) for value in [batch.get("species"), batch.get("cultivar"), batch.get("growth_stage")] if value]
        if details:
            ui.label(" · ".join(details)).classes("text-xs opacity-70")
        if context.plant.additional_count:
            ui.badge(_("+{count} more batches", count=context.plant.additional_count), color="blue").props("outline")


def _render_pending_commands(
    context: ZoneContext,
    *,
    on_approve: Callable[[str], object],
    on_reject: Callable[[str], object],
    control_mode: str | None = None,
) -> None:
    with ui.card().classes("greenhouse-card w-full p-3"):
        ui.label(_("Pending Proposals")).classes("font-semibold")
        if not context.pending_commands:
            ui.label(_("No pending proposals for this zone.")).classes("text-xs opacity-60")
            return
        with ui.column().classes("w-full gap-2 mt-2"):
            for command in context.pending_commands:
                proposed_action_card(command_to_action(command, context, current_mode=control_mode), on_approve=on_approve, on_reject=on_reject)
