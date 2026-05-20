"""Plants page -- plant batches, profiles, growth stages, zone assignments."""

from __future__ import annotations

from typing import Any

import httpx
from nicegui import ui

from app.i18n.core import _
from app.ui.api_client import api_client, response_error
from app.ui.components.design import empty_state, page_container, page_hero, section_card
from app.ui.components.plant_profile_helpers import soil_moisture_order_valid
from app.ui.layouts.main_layout import main_layout


@ui.page("/plants")
async def plants() -> None:
    """Render the plants management page."""
    main_layout()

    profiles: list[dict[str, Any]] = []
    editing_profile_id: str | None = None

    with page_container():
        page_hero(
            _("Plants"),
            _("Set crop profile thresholds and connect growth stages to greenhouse zones."),
            icon="local_florist",
            meta=_("Crop planning"),
        )

        with section_card(
            _("Soil Moisture Profile"),
            _("Create editable starter thresholds for a crop and growth stage."),
            icon="spa",
        ):
            with ui.column().classes("w-full gap-3 mt-4"):
                with ui.row().classes("w-full gap-4 flex-wrap items-end"):
                    crop_name = ui.input(_("Crop name"), placeholder=_("Tomato")).classes("min-w-[220px] flex-1")
                    growth_stage = ui.input(_("Growth stage"), placeholder=_("seedling")).classes("min-w-[180px] flex-1")
                    soil_min = ui.number(_("Minimum soil moisture (%)"), value=40.0, min=0, max=100).classes("min-w-[180px] flex-1")
                    soil_opt = ui.number(_("Optimal soil moisture (%)"), value=55.0, min=0, max=100).classes("min-w-[180px] flex-1")
                    soil_max = ui.number(_("Maximum soil moisture (%)"), value=70.0, min=0, max=100).classes("min-w-[180px] flex-1")
                description = ui.textarea(_("Description"), placeholder=_("Editable starter values; verify against crop requirements.")).classes("w-full")
                with ui.row().classes("gap-2 flex-wrap"):
                    save_button = ui.button(_("Create profile"), icon="save", on_click=lambda: ui.timer(0, save_profile, once=True)).props("color=primary")
                    ui.button(_("Seed default values"), icon="water_drop", on_click=lambda: seed_form_defaults()).props("outline")
                    ui.button(_("Clear"), icon="clear", on_click=lambda: clear_form()).props("outline")
                ui.label(_("Default values are editable starter thresholds, not guaranteed agronomic recommendations.")).classes("text-xs opacity-60")

        with section_card(
            _("Plant Profiles"),
            _("Reusable environmental targets for crops and growth stages."),
            icon="list_alt",
        ):
            profile_list = ui.column().classes("w-full gap-3 mt-4")

    def notify(message: str, kind: str = "info") -> None:
        ui.notify(message, type=kind, position="top", timeout=5000)

    def value_or_none(value: Any) -> float | None:
        return float(value) if value is not None else None

    def clear_form() -> None:
        nonlocal editing_profile_id
        editing_profile_id = None
        crop_name.set_value("")
        growth_stage.set_value("")
        soil_min.set_value(40.0)
        soil_opt.set_value(55.0)
        soil_max.set_value(70.0)
        description.set_value("")
        save_button.set_text(_("Create profile"))

    def seed_form_defaults() -> None:
        soil_min.set_value(40.0)
        soil_opt.set_value(55.0)
        soil_max.set_value(70.0)
        notify(_("Default soil moisture values seeded. Review them before saving."), "info")

    def edit_profile(profile: dict[str, Any]) -> None:
        nonlocal editing_profile_id
        editing_profile_id = str(profile["id"])
        crop_name.set_value(profile.get("crop_name") or "")
        growth_stage.set_value(profile.get("growth_stage") or "")
        soil_min.set_value(profile.get("soil_moisture_min"))
        soil_opt.set_value(profile.get("soil_moisture_opt"))
        soil_max.set_value(profile.get("soil_moisture_max"))
        description.set_value(profile.get("description") or "")
        save_button.set_text(_("Update profile"))

    def display_value(value: Any) -> str:
        return "—" if value is None else str(value)

    def render_profiles() -> None:
        profile_list.clear()
        with profile_list:
            if not profiles:
                empty_state(
                    _("No plant profiles yet"),
                    _("Create a crop profile to compare soil moisture readings against editable thresholds."),
                    icon="spa",
                )
                return
            for profile in profiles:
                with ui.card().classes("greenhouse-card w-full p-4"):
                    with ui.row().classes("w-full items-start justify-between gap-3"):
                        with ui.column().classes("gap-1"):
                            title = profile.get("crop_name") or _("Unnamed crop")
                            stage = profile.get("growth_stage") or _("Any stage")
                            ui.label(f"{title} · {stage}").classes("font-semibold")
                            ui.label(profile.get("description") or _("No description provided.")).classes("text-sm opacity-65")
                            with ui.row().classes("gap-2 flex-wrap mt-1"):
                                ui.badge(_("Min {value}%", value=display_value(profile.get("soil_moisture_min"))), color="blue").props("outline")
                                ui.badge(_("Optimal {value}%", value=display_value(profile.get("soil_moisture_opt"))), color="green").props("outline")
                                ui.badge(_("Max {value}%", value=display_value(profile.get("soil_moisture_max"))), color="orange").props("outline")
                        ui.button(_("Edit"), icon="edit", on_click=lambda p=profile: edit_profile(p)).props("outline dense")

    async def load_profiles() -> None:
        nonlocal profiles
        try:
            async with api_client(timeout=10.0) as client:
                response = await client.get("/api/plant-profiles")
        except httpx.HTTPError as exc:
            notify(_("Failed to load plant profiles: {error}", error=exc), "negative")
            return
        if response.status_code != 200:
            notify(_("Failed to load plant profiles: {error}", error=response_error(response)), "negative")
            return
        profiles = response.json()
        render_profiles()

    async def save_profile() -> None:
        if not crop_name.value:
            notify(_("Enter a crop name before saving the profile."), "warning")
            return
        minimum = value_or_none(soil_min.value)
        optimum = value_or_none(soil_opt.value)
        maximum = value_or_none(soil_max.value)
        if not soil_moisture_order_valid(minimum, optimum, maximum):
            notify(_("Soil moisture values must be ordered from minimum to optimal to maximum."), "warning")
            return

        payload = {
            "crop_name": crop_name.value,
            "growth_stage": growth_stage.value or None,
            "soil_moisture_min": minimum,
            "soil_moisture_opt": optimum,
            "soil_moisture_max": maximum,
            "description": description.value or None,
        }
        async with api_client(timeout=10.0) as client:
            if editing_profile_id:
                response = await client.patch(f"/api/plant-profiles/{editing_profile_id}", json=payload)
            else:
                response = await client.post("/api/plant-profiles", json=payload)
        if response.status_code not in {200, 201}:
            notify(_("Save plant profile failed: {error}", error=response_error(response)), "negative")
            return
        notify(_("Plant profile saved"), "positive")
        clear_form()
        await load_profiles()

    await load_profiles()


__all__ = ["plants"]
