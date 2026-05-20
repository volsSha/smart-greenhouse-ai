"""Zone, plant, and device registration page."""

from __future__ import annotations

from secrets import token_urlsafe
from typing import Any

import httpx
from nicegui import ui

from app.i18n.core import _
from app.ui.api_client import api_client, response_error
from app.ui.components.control_panel_state import ScopeOption, build_scope_options
from app.ui.components.design import empty_state, page_container, page_hero, section_card
from app.ui.components.plant_profile_helpers import (
    default_soil_moisture_payload,
    empty_soil_moisture_fields,
    find_matching_profile,
    profile_label,
)
from app.ui.layouts.main_layout import main_layout


@ui.page("/zones")
async def zone_management() -> None:
    main_layout()

    groups: list[ScopeOption] = []
    greenhouses: list[ScopeOption] = []
    zones: list[dict[str, Any]] = []
    edge_nodes: list[dict[str, Any]] = []
    plants: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    selected_group: ScopeOption | None = None
    selected_greenhouse: ScopeOption | None = None
    group_label_to_id: dict[str, str] = {}
    greenhouse_label_to_id: dict[str, str] = {}
    profile_label_to_id: dict[str, str] = {}

    with page_container():
        page_hero(
            _("Zones and Plants"),
            _("Register real zones, inspect simulator-generated zones, and copy Wokwi MQTT identifiers."),
            icon="view_in_ar",
            meta=_("Registry"),
        )

        with section_card(_("Scope"), _("Choose where new zones and devices should be registered."), icon="hub"):
            with ui.row().classes("w-full gap-4 mt-4 flex-wrap items-end"):
                group_select = ui.select(label=_("Group"), options=[], on_change=lambda e: choose_group(e.value)).classes("min-w-[220px] flex-1")
                greenhouse_select = ui.select(label=_("Greenhouse"), options=[], on_change=lambda e: choose_greenhouse(e.value)).classes("min-w-[220px] flex-1")
                ui.button(_("Refresh"), icon="refresh", on_click=lambda: ui.timer(0, reload_all, once=True)).props("outline")

        with section_card(_("Create Zone"), _("Real zones are used by MQTT devices; simulator zones are created automatically when the simulator starts."), icon="add_location_alt"):
            with ui.row().classes("w-full gap-4 mt-4 flex-wrap items-end"):
                zone_name = ui.input(_("Zone name"), placeholder=_("north-bed")).classes("min-w-[220px] flex-1")
                zone_description = ui.input(_("Description"), placeholder=_("Tomatoes, row A")).classes("min-w-[260px] flex-1")
                source_select = ui.select(label=_("Type"), options={"real": _("Real MQTT zone"), "simulator": _("Simulator zone")}, value="real").classes("w-48")
                ui.button(_("Add zone"), icon="add", on_click=lambda: ui.timer(0, create_zone, once=True)).props("color=primary")

        with section_card(_("Create Plant Batch"), _("Attach plants to a zone so the control page can show plant context."), icon="local_florist"):
            with ui.row().classes("w-full gap-4 mt-4 flex-wrap items-end"):
                plant_zone_select = ui.select(label=_("Zone"), options=[]).classes("min-w-[220px] flex-1")
                profile_select = ui.select(label=_("Profile"), options=[], on_change=lambda e: select_profile(e.value)).classes("min-w-[220px] flex-1")
                plant_name = ui.input(_("Batch name"), placeholder=_("Tomato batch")).classes("min-w-[220px] flex-1")
                plant_species = ui.input(_("Species"), placeholder=_("Tomato")).classes("min-w-[180px] flex-1")
                growth_stage = ui.input(_("Growth stage"), placeholder=_("vegetative")).classes("min-w-[180px] flex-1")
                ui.button(_("Add plants"), icon="add", on_click=lambda: ui.timer(0, create_plant_batch, once=True)).props("color=primary")
                ui.button(_("Seed default profile values"), icon="water_drop", on_click=lambda: ui.timer(0, seed_default_profile_values, once=True)).props("outline")
                ui.button(_("Clear profile"), icon="link_off", on_click=lambda: clear_profile()).props("outline")
            ui.label(_("Select a profile to fill species and growth stage, or seed editable starter profile values first.")).classes("text-xs opacity-60 mt-2")

        with section_card(_("Wokwi / MQTT Setup"), _("Use these identifiers in firmware/wokwi-greenhouse-zone/config.py and publish telemetry to the matching topic."), icon="developer_board"):
            with ui.column().classes("w-full gap-2 mt-4"):
                ui.label(_("1. Use a public MQTT broker, such as Mosquitto on a VPS."))
                ui.label(_("2. Copy MQTT_HOST, MQTT_PORT, MQTT_USER, and MQTT_PASSWORD into config.py."))
                ui.label(_("3. Set GROUP_ID, GREENHOUSE_ID, ZONE_ID, MQTT_USERNAME, and MQTT_TOKEN from a real zone below."))
                ui.label(_("4. Wokwi sends telemetry; approved MQTT-mode commands are published back to the zone command topic."))
            topic_label = ui.label("").classes("text-xs font-mono mt-3 opacity-70")

        with section_card(_("Registered Zones"), _("Simulator-generated rows survive page refresh and can be deleted here when no longer needed."), icon="list_alt"):
            zone_list = ui.column().classes("w-full gap-3 mt-4")

    def notify(message: str, kind: str = "info") -> None:
        ui.notify(message, type=kind, position="top", timeout=5000)

    def option_maps(options: list[ScopeOption]) -> tuple[dict[str, str], dict[str, str]]:
        label_to_id = {option.label: option.id for option in options}
        id_to_label = {option.id: option.label for option in options}
        return label_to_id, id_to_label

    def option_by_id(options: list[ScopeOption], option_id: str | None) -> ScopeOption | None:
        if option_id is None:
            return None
        return next((option for option in options if option.id == option_id), None)

    def set_group_options() -> None:
        nonlocal group_label_to_id
        group_label_to_id, id_to_label = option_maps(groups)
        group_select.set_options(list(group_label_to_id))
        group_select.set_value(id_to_label.get(selected_group.id) if selected_group else None)

    def set_greenhouse_options() -> None:
        nonlocal greenhouse_label_to_id
        greenhouse_label_to_id, id_to_label = option_maps(greenhouses)
        greenhouse_select.set_options(list(greenhouse_label_to_id))
        greenhouse_select.set_value(id_to_label.get(selected_greenhouse.id) if selected_greenhouse else None)
        greenhouse_select.set_enabled(bool(selected_group and greenhouses))

    def set_zone_options() -> None:
        options = {zone["id"]: zone.get("name", zone["id"]) for zone in zones}
        plant_zone_select.set_options(options)
        plant_zone_select.set_value(next(iter(options), None))

    def set_profile_options(selected_profile_id: str | None = None) -> None:
        nonlocal profile_label_to_id
        profile_label_to_id = {profile_label(profile): str(profile["id"]) for profile in profiles}
        id_to_label = {profile_id: label for label, profile_id in profile_label_to_id.items()}
        profile_select.set_options(list(profile_label_to_id))
        profile_select.set_value(id_to_label.get(selected_profile_id) if selected_profile_id else None)

    def profile_by_id(profile_id: str | None) -> dict[str, Any] | None:
        if profile_id is None:
            return None
        return next((profile for profile in profiles if str(profile.get("id")) == profile_id), None)

    def apply_profile(profile: dict[str, Any]) -> None:
        plant_species.set_value(profile.get("crop_name") or "")
        growth_stage.set_value(profile.get("growth_stage") or "")

    def select_profile(label: str | None) -> None:
        profile = profile_by_id(profile_label_to_id.get(label or ""))
        if profile is not None:
            apply_profile(profile)

    def clear_profile() -> None:
        profile_select.set_value(None)

    def node_for_zone(zone: dict[str, Any]) -> dict[str, Any] | None:
        zone_id = str(zone["id"])
        return next((node for node in edge_nodes if str(node.get("node_key", "")).endswith(zone_id)), None)

    def render_zones() -> None:
        zone_list.clear()
        topic_label.set_text("")
        with zone_list:
            if selected_greenhouse is None:
                empty_state(_("No greenhouse selected"), _("Select a greenhouse before managing zones."), icon="yard")
                return
            if not zones:
                empty_state(_("No zones yet"), _("Create a real zone here or start the simulator to provision simulator zones."), icon="view_in_ar")
                return
            for zone in zones:
                node = node_for_zone(zone)
                with ui.card().classes("greenhouse-card w-full p-4"):
                    with ui.row().classes("w-full items-start justify-between gap-3"):
                        with ui.column().classes("gap-1"):
                            ui.label(zone.get("name", zone["id"])).classes("font-semibold")
                            ui.label(str(zone["id"])).classes("text-xs font-mono opacity-60")
                            ui.badge(_("Simulator") if zone.get("source_type") == "simulator" else _("Real MQTT"), color="orange" if zone.get("source_type") == "simulator" else "green")
                            if node:
                                ui.label(f"MQTT_USERNAME={node.get('mqtt_username') or node.get('node_key')}").classes("text-xs font-mono")
                                ui.label(f"MQTT_TOKEN={node.get('mqtt_token') or 'not generated'}").classes("text-xs font-mono")
                        with ui.column().classes("gap-2 items-end"):
                            ui.button(_("Show topic"), icon="topic", on_click=lambda z=zone: show_topic(z)).props("outline dense")
                            ui.button(_("Delete"), icon="delete", on_click=lambda z=zone: ui.timer(0, lambda: delete_zone(z), once=True)).props("outline dense color=negative")

    def show_topic(zone: dict[str, Any]) -> None:
        if selected_group is None or selected_greenhouse is None:
            return
        topic_label.set_text(f"greenhouse-groups/{selected_group.id}/greenhouses/{selected_greenhouse.id}/zones/{zone['id']}/telemetry")

    async def load_groups() -> None:
        nonlocal groups, selected_group
        async with api_client(timeout=10.0) as client:
            response = await client.get("/api/groups")
        if response.status_code != 200:
            notify(_("Failed to load groups: {error}", error=response_error(response)), "negative")
            return
        groups = build_scope_options(response.json(), fallback_prefix=_("Group"))
        selected_group = groups[0] if groups else None
        set_group_options()

    async def load_greenhouses() -> None:
        nonlocal greenhouses, selected_greenhouse
        greenhouses = []
        selected_greenhouse = None
        if selected_group is None:
            set_greenhouse_options()
            return
        async with api_client(timeout=10.0) as client:
            response = await client.get(f"/api/groups/{selected_group.id}/greenhouses")
        if response.status_code != 200:
            notify(_("Failed to load greenhouses: {error}", error=response_error(response)), "negative")
            return
        greenhouses = build_scope_options(response.json(), fallback_prefix=_("Greenhouse"))
        selected_greenhouse = greenhouses[0] if greenhouses else None
        set_greenhouse_options()

    async def load_registry() -> None:
        nonlocal zones, edge_nodes, plants, profiles
        zones = []
        edge_nodes = []
        plants = []
        profiles = []
        if selected_group is None or selected_greenhouse is None:
            set_zone_options()
            set_profile_options()
            render_zones()
            return
        try:
            async with api_client(timeout=10.0) as client:
                zones_response = await client.get(f"/api/groups/{selected_group.id}/greenhouses/{selected_greenhouse.id}/zones")
                nodes_response = await client.get(f"/api/groups/{selected_group.id}/devices/edge-nodes")
                plants_response = await client.get(f"/api/groups/{selected_group.id}/plant-batches")
                profiles_response = await client.get("/api/plant-profiles")
            zones = zones_response.json() if zones_response.status_code == 200 else []
            edge_nodes = nodes_response.json() if nodes_response.status_code == 200 else []
            plants = plants_response.json() if plants_response.status_code == 200 else []
            profiles = profiles_response.json() if profiles_response.status_code == 200 else []
        except httpx.HTTPError as exc:
            notify(_("Failed to load registry: {error}", error=exc), "negative")
        selected_profile_id = profile_label_to_id.get(profile_select.value or "")
        set_zone_options()
        set_profile_options(selected_profile_id)
        render_zones()

    async def create_zone() -> None:
        if selected_group is None or selected_greenhouse is None or not zone_name.value:
            notify(_("Select a greenhouse and enter a zone name."), "warning")
            return
        async with api_client(timeout=10.0) as client:
            zone_response = await client.post(
                f"/api/groups/{selected_group.id}/greenhouses/{selected_greenhouse.id}/zones",
                json={"name": zone_name.value, "description": zone_description.value or None, "source_type": source_select.value},
            )
            if zone_response.status_code != 201:
                notify(_("Create zone failed: {error}", error=response_error(zone_response)), "negative")
                return
            zone = zone_response.json()
            node_key = f"{source_select.value}-{zone['id']}"
            await client.post(
                f"/api/groups/{selected_group.id}/devices/edge-nodes",
                json={
                    "greenhouse_id": selected_greenhouse.id,
                    "node_key": node_key,
                    "name": f"{zone_name.value} node",
                    "node_type": "simulator" if source_select.value == "simulator" else "esp32",
                    "mqtt_username": node_key,
                    "mqtt_token": token_urlsafe(24),
                },
            )
        zone_name.set_value("")
        zone_description.set_value("")
        notify(_("Zone created"), "positive")
        await load_registry()

    async def create_plant_batch() -> None:
        if selected_group is None or not plant_zone_select.value or not plant_name.value:
            notify(_("Select a zone and enter a plant batch name."), "warning")
            return
        profile_id = profile_label_to_id.get(profile_select.value or "")
        async with api_client(timeout=10.0) as client:
            response = await client.post(
                f"/api/groups/{selected_group.id}/plant-batches",
                json={
                    "zone_id": plant_zone_select.value,
                    "profile_id": profile_id,
                    "name": plant_name.value,
                    "species": plant_species.value or None,
                    "growth_stage": growth_stage.value or None,
                },
            )
        if response.status_code != 201:
            notify(_("Create plant batch failed: {error}", error=response_error(response)), "negative")
            return
        plant_name.set_value("")
        notify(_("Plant batch created. Use the separate seed button to add editable default profile values."), "positive")
        await load_registry()

    async def seed_default_profile_values() -> None:
        species = (plant_species.value or "").strip()
        stage = (growth_stage.value or "").strip() or None
        if not species:
            notify(_("Enter species before seeding default profile values."), "warning")
            return
        seeded_profile_id: str | None = None
        async with api_client(timeout=10.0) as client:
            profile = find_matching_profile(profiles, species, stage)
            if profile is None:
                response = await client.post(
                    "/api/plant-profiles",
                    json=default_soil_moisture_payload(species, stage),
                )
            else:
                payload = empty_soil_moisture_fields(profile)
                if not payload:
                    seeded_profile_id = str(profile["id"])
                    set_profile_options(seeded_profile_id)
                    apply_profile(profile)
                    notify(_("Matching profile already has soil moisture values; selected it for this batch."), "info")
                    return
                response = await client.patch(f"/api/plant-profiles/{profile['id']}", json=payload)
        if response.status_code not in {200, 201}:
            notify(_("Seed default profile values failed: {error}", error=response_error(response)), "negative")
            return
        seeded_profile_id = str(response.json()["id"])
        notify(_("Editable default profile values seeded and selected for this batch."), "positive")
        await load_registry()
        seeded_profile = profile_by_id(seeded_profile_id)
        set_profile_options(seeded_profile_id)
        if seeded_profile is not None:
            apply_profile(seeded_profile)

    async def delete_zone(zone: dict[str, Any]) -> None:
        if selected_group is None or selected_greenhouse is None:
            return
        async with api_client(timeout=10.0) as client:
            response = await client.delete(f"/api/groups/{selected_group.id}/greenhouses/{selected_greenhouse.id}/zones/{zone['id']}")
        if response.status_code not in {200, 204}:
            notify(_("Delete zone failed: {error}", error=response_error(response)), "negative")
            return
        notify(_("Zone deleted"), "warning")
        await load_registry()

    def choose_group(label: str | None) -> None:
        nonlocal selected_group
        selected_group = option_by_id(groups, group_label_to_id.get(label or ""))
        ui.timer(0, reload_for_group, once=True)

    def choose_greenhouse(label: str | None) -> None:
        nonlocal selected_greenhouse
        selected_greenhouse = option_by_id(greenhouses, greenhouse_label_to_id.get(label or ""))
        ui.timer(0, load_registry, once=True)

    async def reload_for_group() -> None:
        await load_greenhouses()
        await load_registry()

    async def reload_all() -> None:
        await load_groups()
        await load_greenhouses()
        await load_registry()

    await reload_all()


__all__ = ["zone_management"]
