"""Tool call trace components for AI chat transparency.

Provides collapsible panels that display which tools the AI agent
called, their arguments, status, duration, and result summaries.
"""

from __future__ import annotations

import json
from typing import Any

from nicegui import ui

from app.i18n.core import _


_STATUS_CONFIG: dict[str, dict[str, str]] = {
    "ok": {"icon": "check_circle", "color": "#4caf50", "label": "Success"},
    "error": {"icon": "error", "color": "#f44336", "label": "Error"},
}


def _truncate_value(value: Any, max_length: int = 200) -> str:
    """Truncate a value for display in the tool call trace."""
    if value is None:
        return "null"
    text = json.dumps(value, default=str, ensure_ascii=False)
    if len(text) > max_length:
        return f"{text[:max_length]}..."
    return text


def _format_duration(duration_ms: int | None) -> str:
    """Format duration in milliseconds to a human-readable string."""
    if duration_ms is None:
        return ""
    if duration_ms < 1000:
        return f"{duration_ms}ms"
    return f"{duration_ms / 1000:.1f}s"


def _status_label(status: str) -> str:
    labels = {
        "ok": _("Success"),
        "error": _("Error"),
    }
    return labels.get(status, labels["ok"])


def tool_call_item(tool_call: dict[str, Any]) -> None:
    """Render a single tool call with name, arguments, status, duration, and result.

    Parameters:
        tool_call: Dict with keys:
            - tool_name (str): Name of the tool that was called
            - arguments (dict, optional): Arguments passed to the tool
            - result (dict or str, optional): Result summary from the tool
            - status (str): 'ok' or 'error'
            - error (str, optional): Error message if status is 'error'
            - duration_ms (int, optional): Execution duration in milliseconds
    """
    tool_name = tool_call.get("tool_name", "unknown")
    arguments = tool_call.get("arguments", {})
    result = tool_call.get("result")
    status = tool_call.get("status", "ok")
    error = tool_call.get("error")
    duration_ms = tool_call.get("duration_ms")

    config = _STATUS_CONFIG.get(status, _STATUS_CONFIG["ok"])

    with ui.card().classes("w-full").style("border-left: 3px solid {color}".format(color=config["color"])):
        # Header row: icon, tool name, status, duration
        with ui.row().classes("items-center w-full gap-2"):
            ui.icon(config["icon"], size="1rem").style(f"color: {config['color']}")
            ui.label(tool_name).classes("text-sm font-mono font-semibold")
            ui.label(_status_label(status)).classes("text-xs").style(f"color: {config['color']}")
            if duration_ms is not None:
                ui.label(_format_duration(duration_ms)).classes("text-xs opacity-50 ml-auto")

        # Arguments
        if arguments:
            with ui.expansion(_("Arguments"), icon="code").classes("w-full mt-1"):
                ui.label(_truncate_value(arguments)).classes(
                    "text-xs font-mono bg-gray-50 p-2 rounded w-full overflow-x-auto"
                )

        # Result
        if result is not None:
            with ui.expansion(_("Result"), icon="data_object").classes("w-full mt-1"):
                ui.label(_truncate_value(result)).classes(
                    "text-xs font-mono bg-gray-50 p-2 rounded w-full overflow-x-auto"
                )

        # Error
        if error:
            ui.label(error).classes("text-xs text-red-600 mt-1 bg-red-50 p-2 rounded")


def tool_call_panel(tool_calls: list[dict[str, Any]]) -> None:
    """Render a collapsible panel showing all tool calls for a response.

    Parameters:
        tool_calls: List of tool call dicts as described in :func:`tool_call_item`.
    """
    if not tool_calls:
        return

    total_duration = sum(
        tc.get("duration_ms", 0) or 0 for tc in tool_calls
    )
    error_count = sum(1 for tc in tool_calls if tc.get("status") == "error")

    summary_parts = [_("{count} tool calls", count=len(tool_calls))]
    if total_duration:
        summary_parts.append(_("{duration} total", duration=_format_duration(total_duration)))
    if error_count:
        summary_parts.append(_("{count} errors", count=error_count))

    summary = ", ".join(summary_parts)

    with ui.expansion(
        _("Tool Calls: {summary}", summary=summary),
        icon="construction",
    ).classes("w-full"):
        with ui.column().classes("w-full gap-2"):
            for tc in tool_calls:
                tool_call_item(tc)
