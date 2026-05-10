"""Plants page -- plant batches, profiles, growth stages, zone assignments."""

from nicegui import ui

from app.i18n.core import _
from app.ui.layouts.main_layout import main_layout


@ui.page("/plants")
async def plants() -> None:
    """Render the plants management page."""
    main_layout()
    ui.label(_("Plants")).classes("text-2xl font-bold mt-6")
    ui.label(_("Plant batches, profiles, growth stages, and zone assignments.")).classes(
        "text-sm opacity-70 mt-2"
    )

    with ui.row().classes("w-full mt-6 gap-4"):
        # Plant Profiles section
        with ui.card().classes("w-1/2"):
            ui.label(_("Plant Profiles")).classes("text-lg font-bold")
            ui.label(
                _("Manage reusable environmental condition profiles for different crops.")
            ).classes("text-sm opacity-70 mt-1")
            ui.label(_("Placeholder -- profiles management will appear here.")).classes(
                "text-xs italic mt-4"
            )

        # Plant Batches section
        with ui.card().classes("w-1/2"):
            ui.label(_("Plant Batches")).classes("text-lg font-bold")
            ui.label(
                _("Track growing batches across greenhouse zones.")
            ).classes("text-sm opacity-70 mt-1")
            ui.label(_("Placeholder -- batch management will appear here.")).classes(
                "text-xs italic mt-4"
            )

    ui.label(_("Placeholder -- full plant management UI will be implemented.")).classes(
        "text-xs italic mt-6"
    )
