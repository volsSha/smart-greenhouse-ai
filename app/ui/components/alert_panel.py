"""Alert panel components for the Smart Greenhouse dashboard.

Provides alert list and item display widgets with severity badges.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from nicegui import ui

from app.i18n.core import _


_SEVERITY_CONFIG: dict[str, dict[str, str]] = {
    "critical": {"icon": "error", "color": "#f44336", "bg": "#ffebee", "text": "#b71c1c"},
    "warning": {"icon": "warning", "color": "#ff9800", "bg": "#fff3e0", "text": "#e65100"},
    "info": {"icon": "info", "color": "#2196f3", "bg": "#e3f2fd", "text": "#0d47a1"},
}


def _format_timestamp(ts: Any) -> str:
    """Format a timestamp value into a human-readable string."""
    if ts is None:
        return ""
    if isinstance(ts, datetime):
        return ts.strftime("%H:%M:%S")
    return str(ts)[-8:] if len(str(ts)) >= 8 else str(ts)


def alert_item(alert: dict[str, Any]) -> None:
    """Render a single alert with icon, title, message, and timestamp.

    Parameters:
        alert: Dict with keys:
            - severity (str): 'critical', 'warning', or 'info'
            - title (str): Alert title
            - message (str, optional): Alert description
            - timestamp (datetime or str, optional): When the alert was raised
            - zone_id (str, optional): Affected zone
            - greenhouse_id (str, optional): Affected greenhouse
    """
    severity = alert.get("severity", "info").lower()
    config = _SEVERITY_CONFIG.get(severity, _SEVERITY_CONFIG["info"])

    title = alert.get("title", _("Unknown Alert"))
    message = alert.get("message", "")
    timestamp = alert.get("timestamp")
    zone_id = alert.get("zone_id")
    greenhouse_id = alert.get("greenhouse_id")

    with ui.row().classes("w-full items-start gap-2 p-2 rounded").style(
        f"background-color: {config['bg']}"
    ):
        ui.icon(config["icon"], size="1.2rem").style(f"color: {config['color']}")

        with ui.column().classes("flex-1 gap-0.5"):
            with ui.row().classes("items-center gap-2"):
                ui.label(title).classes("text-sm font-semibold").style(
                    f"color: {config['text']}"
                )
                if greenhouse_id:
                    ui.label(greenhouse_id).classes("text-xs opacity-60")
                if zone_id:
                    ui.label(f"/ {zone_id}").classes("text-xs opacity-60")
                if timestamp:
                    ui.label(_format_timestamp(timestamp)).classes(
                        "text-xs opacity-50 ml-auto"
                    )

            if message:
                ui.label(message).classes("text-xs opacity-70")


def alert_panel(alerts: list[dict[str, Any]]) -> None:
    """Render a panel listing active alerts with severity badges.

    Parameters:
        alerts: List of alert dicts as described in :func:`alert_item`.
    """
    with ui.card().classes("w-full"):
        ui.label(_("Active Alerts")).classes("text-lg font-bold")

        if not alerts:
            ui.label(_("No active alerts")).classes("text-sm opacity-50 mt-2")
            return

        # Sort by severity: critical first, then warning, then info
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        sorted_alerts = sorted(
            alerts,
            key=lambda a: severity_order.get(a.get("severity", "info").lower(), 99),
        )

        with ui.column().classes("w-full gap-2 mt-2"):
            for alert in sorted_alerts:
                alert_item(alert)
