"""Plants page -- plant batches, profiles, growth stages, zone assignments."""

from nicegui import ui

from app.i18n.core import _
from app.ui.components.design import page_container, page_hero, section_card
from app.ui.layouts.main_layout import main_layout


@ui.page("/plants")
async def plants() -> None:
    """Render the plants management page."""
    main_layout()
    with page_container():
        page_hero(
            _("Plants"),
            _("Plan crop profiles, track batches, and connect growth stages to greenhouse zones."),
            icon="local_florist",
            meta=_("Crop planning"),
        )

        with ui.row().classes("w-full gap-4 flex-wrap"):
            with section_card(
                _("Plant Profiles"),
                _("Reusable environmental targets for crops and growth stages."),
                icon="spa",
                classes="w-1/2 min-w-[320px]",
            ):
                ui.label(_("Profiles will define preferred temperature, humidity, soil moisture, CO2, and light ranges.")).classes("text-sm opacity-65 mt-4")
                ui.badge(_("Planned"), color="green").props("outline")

            with section_card(
                _("Plant Batches"),
                _("Operational batches assigned to zones across the fleet."),
                icon="inventory_2",
                classes="w-1/2 min-w-[320px]",
            ):
                ui.label(_("Batch tracking will connect planting dates, growth stages, and zone assignments." )).classes("text-sm opacity-65 mt-4")
                ui.badge(_("Planned"), color="green").props("outline")

        with section_card(_("Coming Next"), _("This page is ready for the full plant-management workflow without looking unfinished."), icon="event_upcoming"):
            ui.label(_("Use the dashboard and simulator today; crop-specific planning can be added here when APIs are available.")).classes("text-sm opacity-70 mt-3")
