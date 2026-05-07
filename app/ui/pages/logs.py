"""Logs page -- command history and audit log viewer."""

from nicegui import ui

from app.ui.layouts.main_layout import main_layout


@ui.page("/logs")
async def logs() -> None:
    """Render the command logs page.

    Placeholder layout for U9. Full implementation will include:
    - Filterable command history table
    - Status filters (proposed, validated, approved, executed, etc.)
    - Search by actuator, zone, or date range
    - Detailed command view with validation errors
    """
    main_layout()

    ui.label("Command Logs").classes("text-2xl font-bold mt-6")
    ui.label(
        "Audit log of all actuator commands with filtering and search."
    ).classes("text-sm opacity-70 mt-2")

    with ui.card().classes("w-full mt-6"):
        ui.label("Filters").classes("text-lg font-semibold")

        with ui.row().classes("w-full gap-4 mt-4"):
            ui.select(
                label="Status",
                options=[
                    "all",
                    "proposed",
                    "validated",
                    "approved",
                    "executing",
                    "executed",
                    "cancelled",
                    "rejected",
                    "expired",
                    "failed",
                ],
                value="all",
            ).classes("w-48")
            ui.select(
                label="Actuator",
                options=["all", "pump", "fan", "heater", "lamp"],
                value="all",
            ).classes("w-48")
            ui.select(
                label="Source",
                options=["all", "manual", "control_engine", "ai_agent", "safety_override"],
                value="all",
            ).classes("w-48")
            ui.button("Refresh", icon="refresh", color="primary")

    with ui.card().classes("w-full mt-6"):
        ui.label("Command History").classes("text-lg font-semibold")
        ui.label("Command log entries will appear here.").classes(
            "text-sm opacity-70 mt-2"
        )

    ui.label("Placeholder -- full logs UI will be implemented in a later unit.").classes(
        "text-xs italic mt-4"
    )
