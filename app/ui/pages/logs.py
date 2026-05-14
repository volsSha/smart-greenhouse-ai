"""Logs page -- project error log viewer."""

from __future__ import annotations

import json
from typing import Any

import httpx
from nicegui import ui

from app.i18n.core import _
from app.ui.api_client import api_client
from app.ui.layouts.main_layout import main_layout

_LEVEL_COLORS = {
    "error": "red",
    "warning": "orange",
    "info": "blue",
}


def _format_json(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(value, indent=2, ensure_ascii=False, default=str)


@ui.page("/logs")
async def logs() -> None:
    """Render the persisted project error logs page."""
    main_layout()

    ui.label(_("Project Error Logs")).classes("text-2xl font-bold mt-6")
    ui.label(
        _("Database-backed debug and error events captured by the application.")
    ).classes("text-sm opacity-70 mt-2")

    selected_level = {"value": "error"}
    selected_component = {"value": "all"}
    selected_event_type = {"value": "all"}
    content_area = ui.column().classes("w-full gap-3 mt-6")

    async def load_logs() -> None:
        content_area.clear()
        params: dict[str, str | int] = {"limit": 50}
        if selected_level["value"] != "all":
            params["level"] = selected_level["value"]
        if selected_component["value"] != "all":
            params["component"] = selected_component["value"]
        if selected_event_type["value"] != "all":
            params["event_type"] = selected_event_type["value"]

        with content_area:
            spinner = ui.spinner(size="lg").classes("self-center mt-8")

        try:
            async with api_client(timeout=10.0) as client:
                response = await client.get("/api/debug-logs", params=params)
                response.raise_for_status()
                logs_data = response.json()
        except httpx.HTTPError as exc:
            spinner.delete()
            with content_area:
                ui.label(_("Error loading logs: {error}", error=exc)).classes("text-red-500 text-sm")
                ui.label(_("Check that the API and database are available.")).classes("text-xs opacity-50")
            return

        spinner.delete()
        with content_area:
            if not logs_data:
                with ui.column().classes("w-full items-center gap-3 mt-12"):
                    ui.icon("fact_check", size="4rem").classes("opacity-30")
                    ui.label(_("No log entries match the selected filters.")).classes("text-lg opacity-50")
                return

            for entry in logs_data:
                level = entry.get("level", "info")
                color = _LEVEL_COLORS.get(level, "grey")
                with ui.card().classes("w-full"):
                    with ui.row().classes("w-full items-start gap-3"):
                        ui.badge(level.upper(), color=color).classes("mt-1")
                        with ui.column().classes("grow gap-1"):
                            ui.label(entry.get("message") or "").classes("font-semibold")
                            ui.label(
                                _(
                                    "{component} · {event_type} · {created_at}",
                                    component=entry.get("component", "-"),
                                    event_type=entry.get("event_type", "-"),
                                    created_at=entry.get("created_at", "-"),
                                )
                            ).classes("text-xs opacity-60")
                            path = entry.get("path")
                            status_code = entry.get("status_code")
                            if path or status_code:
                                ui.label(
                                    _(
                                        "{method} {path} · HTTP {status_code}",
                                        method=entry.get("method") or "-",
                                        path=path or "-",
                                        status_code=status_code or "-",
                                    )
                                ).classes("text-xs opacity-60")

                    with ui.expansion(_("Details"), icon="bug_report").classes("w-full mt-2"):
                        metadata = entry.get("metadata")
                        error_type = entry.get("error_type")
                        request_id = entry.get("request_id")
                        duration_ms = entry.get("duration_ms")
                        if error_type:
                            ui.label(_("Error type: {error_type}", error_type=error_type)).classes("text-sm")
                        if request_id:
                            ui.label(_("Request ID: {request_id}", request_id=request_id)).classes("text-sm")
                        if duration_ms is not None:
                            ui.label(_("Duration: {duration_ms} ms", duration_ms=round(duration_ms, 2))).classes("text-sm")
                        if metadata:
                            ui.label(_("Metadata")).classes("text-sm font-semibold mt-2")
                            ui.code(_format_json(metadata)).classes("w-full text-xs")
                        if entry.get("stack_trace"):
                            ui.label(_("Stack trace")).classes("text-sm font-semibold mt-2")
                            ui.code(entry["stack_trace"]).classes("w-full text-xs")

    with ui.card().classes("w-full mt-6"):
        ui.label(_("Filters")).classes("text-lg font-semibold")
        with ui.row().classes("w-full gap-4 mt-4 items-end"):
            level_select = ui.select(
                label=_("Level"),
                options=["all", "error", "warning", "info"],
                value=selected_level["value"],
            ).classes("w-48")
            component_select = ui.select(
                label=_("Component"),
                options=["all", "api", "ai_agent"],
                value=selected_component["value"],
            ).classes("w-48")
            event_type_select = ui.select(
                label=_("Event type"),
                options=["all", "unhandled_exception", "http_5xx", "ai_chat_failed"],
                value=selected_event_type["value"],
            ).classes("w-64")

            async def refresh() -> None:
                selected_level["value"] = level_select.value
                selected_component["value"] = component_select.value
                selected_event_type["value"] = event_type_select.value
                await load_logs()

            ui.button(_("Refresh"), icon="refresh", color="primary", on_click=refresh)

    await load_logs()
