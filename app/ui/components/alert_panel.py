"""Alert panel components for the Smart Greenhouse dashboard.

Provides alert list and item display widgets with severity badges.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
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


def alert_item(
    alert: dict[str, Any],
    on_dismiss: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> None:
    """Render a single alert with icon, title, message, and timestamp."""
    severity = alert.get("severity", "info").lower()
    config = _SEVERITY_CONFIG.get(severity, _SEVERITY_CONFIG["info"])

    title = alert.get("title", _("Unknown Alert"))
    message = alert.get("message", "")
    timestamp = alert.get("timestamp") or alert.get("created_at")
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
                    ui.label(_format_timestamp(timestamp)).classes("text-xs opacity-50")

            if message:
                ui.label(message).classes("text-xs opacity-70")

        if on_dismiss:
            async def dismiss_alert() -> None:
                await on_dismiss(alert)

            ui.button(icon="close", on_click=dismiss_alert).props(
                f"flat dense round color=primary aria-label='{_('Dismiss alert')}'"
            )


def alert_panel(
    alerts: list[dict[str, Any]],
    on_dismiss: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    on_dismiss_all: Callable[[], Awaitable[None]] | None = None,
) -> None:
    """Render a panel listing active alerts with severity badges."""
    with ui.card().classes("greenhouse-card w-full p-5"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label(_("Active Alerts")).classes("text-lg font-bold")
            if alerts and on_dismiss_all:
                ui.button(_("Dismiss all"), on_click=on_dismiss_all).props(
                    f"flat dense color=primary aria-label='{_('Dismiss all alerts')}'"
                )
            else:
                ui.icon("notifications_active", size="1.2rem").classes("opacity-45")

        if not alerts:
            with ui.row().classes("items-center gap-2 mt-3"):
                ui.icon("check_circle", size="1.1rem").style("color: #1f7a4d")
                ui.label(_("No active alerts")).classes("text-sm opacity-65")
            return

        # Sort by severity: critical first, then warning, then info
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        sorted_alerts = sorted(
            alerts,
            key=lambda a: severity_order.get(a.get("severity", "info").lower(), 99),
        )

        with ui.column().classes("w-full gap-2 mt-2"):
            for alert in sorted_alerts:
                alert_item(alert, on_dismiss)
