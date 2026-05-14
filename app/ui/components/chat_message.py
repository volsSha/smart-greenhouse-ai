"""Chat message bubble components for the AI chat page.

Provides user, assistant, and system message display widgets following
the established NiceGUI component pattern.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from nicegui import ui

from app.i18n.core import _


def _format_timestamp(ts: Any) -> str:
    """Format a timestamp value into a human-readable string."""
    if ts is None:
        return ""
    if isinstance(ts, datetime):
        return ts.strftime("%H:%M")
    if isinstance(ts, str):
        try:
            parsed = datetime.fromisoformat(ts)
            return parsed.strftime("%H:%M")
        except (ValueError, TypeError):
            return ts[:19] if len(ts) >= 19 else ts
    return str(ts)


def _render_observations(observations: list[str]) -> None:
    """Render a list of observation strings as small labeled items."""
    if not observations:
        return
    with ui.column().classes("gap-1 mt-2"):
        ui.label(_("Observations")).classes("text-xs font-semibold opacity-60")
        for obs in observations:
            with ui.row().classes("items-start gap-1"):
                ui.icon("visibility", size="0.8rem").classes("opacity-40 mt-0.5")
                ui.label(obs).classes("text-xs opacity-80")


def _render_recommendations(recommendations: list[str]) -> None:
    """Render a list of recommendation strings as small labeled items."""
    if not recommendations:
        return
    with ui.column().classes("gap-1 mt-2"):
        ui.label(_("Recommendations")).classes("text-xs font-semibold opacity-60")
        for rec in recommendations:
            with ui.row().classes("items-start gap-1"):
                ui.icon("lightbulb", size="0.8rem").classes("opacity-40 mt-0.5")
                ui.label(rec).classes("text-xs opacity-80")


def _status_badge(status: str) -> None:
    """Render a small status indicator badge for assistant responses."""
    config: dict[str, dict[str, str]] = {
        "ok": {"icon": "check_circle", "color": "#4caf50", "label": _("OK")},
        "insufficient_data": {"icon": "help", "color": "#ff9800", "label": _("Limited Data")},
    }
    entry = config.get(status, config["ok"])
    with ui.row().classes("items-center gap-1"):
        ui.icon(entry["icon"], size="0.8rem").style(f"color: {entry['color']}")
        ui.label(entry["label"]).classes("text-xs").style(f"color: {entry['color']}")


def user_message_bubble(
    content: str,
    timestamp: Any = None,
) -> None:
    """Render a right-aligned blue user message bubble.

    Parameters:
        content: The user's message text.
        timestamp: Optional timestamp for display.
    """
    with ui.row().classes("w-full justify-end"):
        with ui.column().classes("items-end max-w-[75%]"):
            with ui.row().classes("items-end gap-2"):
                if timestamp:
                    ui.label(_format_timestamp(timestamp)).classes("text-xs opacity-40")
                ui.label(content).classes(
                    "px-4 py-2 rounded-2xl rounded-br-sm text-sm"
                ).style("background: linear-gradient(135deg, #1f7a4d, #247a5a); color: white;")


def assistant_message_bubble(
    content: str,
    observations: list[str] | None = None,
    recommendations: list[str] | None = None,
    status: str = "ok",
    timestamp: Any = None,
) -> None:
    """Render a left-aligned assistant message bubble with structured content.

    Parameters:
        content: The assistant's summary text.
        observations: Optional list of observation strings.
        recommendations: Optional list of recommendation strings.
        status: Response status ('ok' or 'insufficient_data').
        timestamp: Optional timestamp for display.
    """
    with ui.row().classes("w-full justify-start"):
        with ui.column().classes("items-start max-w-[80%]"):
            with ui.row().classes("items-start gap-2"):
                ui.icon("smart_toy", size="1.5rem").classes("opacity-40 mt-1")
                with ui.column().classes("gap-1 flex-1"):
                    with ui.row().classes("items-center gap-2 w-full"):
                        ui.label(_("Assistant")).classes("text-xs font-semibold opacity-50")
                        _status_badge(status)
                        if timestamp:
                            ui.label(_format_timestamp(timestamp)).classes(
                                "text-xs opacity-40 ml-auto"
                            )

                    ui.label(content).classes("greenhouse-card text-sm mt-1 p-3")

                    _render_observations(observations or [])
                    _render_recommendations(recommendations or [])


def system_message(content: str) -> None:
    """Render a centered gray system message.

    Parameters:
        content: The system message text.
    """
    with ui.row().classes("w-full justify-center"):
        ui.label(content).classes("text-xs opacity-40 italic")
