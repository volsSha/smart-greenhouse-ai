"""Proposed action card components for the AI chat page.

Displays physical-action proposals from the AI agent with status badges.
Approval/rejection interactions are handled in U14; this module provides
the display-only rendering with status indication.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from app.i18n.core import _


_ACTION_STATUS_CONFIG: dict[str, dict[str, str]] = {
    "pending": {"icon": "schedule", "color": "#ff9800", "bg": "#fff3e0", "label": "Pending Approval"},
    "approved": {"icon": "check_circle", "color": "#4caf50", "bg": "#e8f5e9", "label": "Approved"},
    "rejected": {"icon": "cancel", "color": "#f44336", "bg": "#ffebee", "label": "Rejected"},
    "executed": {"icon": "play_circle", "color": "#2196f3", "bg": "#e3f2fd", "label": "Executed"},
    "expired": {"icon": "timer_off", "color": "#9e9e9e", "bg": "#f5f5f5", "label": "Expired"},
    "failed": {"icon": "error", "color": "#f44336", "bg": "#ffebee", "label": "Failed"},
}


def _status_label(status: str) -> str:
    labels = {
        "pending": _("Pending Approval"),
        "approved": _("Approved"),
        "rejected": _("Rejected"),
        "executed": _("Executed"),
        "expired": _("Expired"),
        "failed": _("Failed"),
    }
    return labels.get(status, labels["pending"])


def _status_badge(status: str) -> None:
    """Render a status badge for a proposed action."""
    config = _ACTION_STATUS_CONFIG.get(status, _ACTION_STATUS_CONFIG["pending"])
    ui.badge(_status_label(status), color=config["color"]).props("outline")


def proposed_action_card(
    action: dict[str, Any],
    on_approve: Callable[[str], Any] | None = None,
    on_reject: Callable[[str], Any] | None = None,
) -> None:
    """Render a card displaying a proposed physical action.

    Parameters:
        action: Dict with keys:
            - group_id (str, optional): Group scope identifier
            - greenhouse_id (str, optional): Greenhouse scope identifier
            - zone_id (str, optional): Zone scope identifier
            - actuator (str): Actuator being controlled (e.g. 'pump', 'fan')
            - action (str): Action to perform (e.g. 'on', 'off', 'set_value')
            - value (str or float, optional): Target value for set_value actions
            - duration_seconds (int, optional): Duration for timed actions
            - reason (str): AI-provided reason for the action
            - status (str, optional): Current status, defaults to 'pending'
            - requires_confirmation (bool, optional): Whether approval is needed
    """
    group_id = action.get("group_id")
    greenhouse_id = action.get("greenhouse_id")
    zone_id = action.get("zone_id")
    actuator = action.get("actuator", "unknown")
    action_type = action.get("action", "unknown")
    value = action.get("value")
    duration = action.get("duration_seconds")
    reason = action.get("reason", "")
    status = action.get("status", "pending")

    config = _ACTION_STATUS_CONFIG.get(status, _ACTION_STATUS_CONFIG["pending"])

    with ui.card().classes("w-full").style(f"border-left: 4px solid {config['color']}"):
        # Header row: actuator, action, status badge
        with ui.row().classes("items-center w-full gap-2"):
            ui.icon(config["icon"], size="1.2rem").style(f"color: {config['color']}")
            ui.label(f"{actuator}").classes("text-sm font-mono font-bold")
            ui.label(f"-> {action_type}").classes("text-sm font-mono")
            if value is not None:
                ui.label(f"= {value}").classes("text-sm font-mono opacity-70")
            if duration is not None:
                ui.label(_("for {duration}s", duration=duration)).classes("text-xs opacity-50")
            _status_badge(status)

        # Scope breadcrumbs
        scope_parts = []
        if group_id:
            scope_parts.append(str(group_id))
        if greenhouse_id:
            scope_parts.append(str(greenhouse_id))
        if zone_id:
            scope_parts.append(str(zone_id))
        if scope_parts:
            with ui.row().classes("items-center gap-1 mt-1"):
                ui.icon("location_on", size="0.8rem").classes("opacity-40")
                ui.label(" / ".join(scope_parts)).classes("text-xs font-mono opacity-50")

        # Reason
        if reason:
            with ui.row().classes("items-start gap-1 mt-2"):
                ui.icon("psychology", size="0.8rem").classes("opacity-40 mt-0.5")
                ui.label(reason).classes("text-xs opacity-70")

        command_id = action.get("command_id") or action.get("id")
        if status in {"pending", "proposed", "validated"} and command_id:
            with ui.row().classes("gap-2 mt-3"):
                ui.button(
                    _("Approve and Execute"),
                    color="positive",
                    on_click=lambda command_id=str(command_id): on_approve(command_id) if on_approve else None,
                ).props("dense")
                ui.button(
                    _("Reject"),
                    color="negative",
                    on_click=lambda command_id=str(command_id): on_reject(command_id) if on_reject else None,
                ).props("dense outline")
