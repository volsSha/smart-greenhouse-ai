"""Control page -- operator panel for actuator proposals and approvals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from nicegui import ui

from app.i18n.core import _
from app.ui.api_client import api_client, response_error
from app.ui.components.control_panel_state import (
    ScopeOption,
    build_scope_options,
    build_zone_context,
    pending_counts_by_zone,
    plant_context_by_zone,
    telemetry_by_zone,
)
from app.ui.components.design import empty_state, page_container, page_hero, section_card
from app.ui.components.greenhouse_map import build_greenhouse_map_model, render_greenhouse_map
from app.ui.components.zone_control_drawer import command_to_action, render_zone_control_drawer
from app.ui.layouts.main_layout import main_layout


@ui.page("/control")
async def control() -> None:
    """Render actuator control page."""
    main_layout()

    groups: list[ScopeOption] = []
    greenhouses: list[ScopeOption] = []
    zones: list[ScopeOption] = []
    selected_group: ScopeOption | None = None
    selected_greenhouse: ScopeOption | None = None
    selected_zone: ScopeOption | None = None
    telemetry: dict[str, dict[str, Any]] = {}
    plant_contexts = {}
    commands: list[dict[str, Any]] = []
    demo_mode = False
    control_mode: str | None = None
    control_mode_loaded = False
    control_mode_error: str | None = None
    simulator_running = False
    group_label_to_id: dict[str, str] = {}
    greenhouse_label_to_id: dict[str, str] = {}

    with page_container():
        page_hero(
            _("Actuator Control"),
            _("Select greenhouse zones visually, propose bounded actuator changes, and keep approval as the safety gate."),
            icon="tune",
            meta=_("Operator panel"),
        )

        with section_card(_("Scope"), _("Choose the group and greenhouse, then select zones from the map."), icon="hub"):
            with ui.row().classes("w-full gap-4 mt-4 flex-wrap items-end"):
                group_select = ui.select(label=_("Group"), options=[], on_change=lambda e: choose_group(e.value)).classes("min-w-[220px] flex-1")
                greenhouse_select = ui.select(label=_("Greenhouse"), options=[], on_change=lambda e: choose_greenhouse(e.value)).classes("min-w-[220px] flex-1")
                refresh_button = ui.button(_("Refresh"), icon="refresh", on_click=lambda: schedule_refresh()).props("outline")
            scope_status = ui.row().classes("w-full gap-2 mt-3 flex-wrap")
            mode_status = ui.row().classes("w-full gap-2 mt-2 flex-wrap")

        with ui.row().classes("control-operator-layout w-full gap-4 items-start"):
            with section_card(_("Greenhouse Overview"), _("Click a zone to inspect context and propose changes."), icon="grid_view", classes="control-map-section flex-1"):
                map_area = ui.column().classes("w-full gap-3 mt-4")
            drawer_area = ui.column().classes("control-drawer-section w-full lg:w-[420px] gap-4")

        with section_card(_("Recent Command Outcomes"), _("Completed, rejected, failed, and expired commands remain secondary to selected-zone proposals."), icon="history"):
            recent_area = ui.column().classes("w-full gap-2 mt-4")

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

    def selected_or_first(options: list[ScopeOption], previous_id: str | None) -> ScopeOption | None:
        return option_by_id(options, previous_id) or (options[0] if options else None)

    def enable_demo_mode() -> None:
        nonlocal groups, greenhouses, zones, selected_group, selected_greenhouse, selected_zone, telemetry, plant_contexts, commands, demo_mode
        demo_mode = True
        groups = [ScopeOption(id="00000000-0000-0000-0000-000000000101", label=_("Demo Group"))]
        greenhouses = [ScopeOption(id="00000000-0000-0000-0000-000000000102", label=_("Demo Greenhouse"))]
        zones = [
            ScopeOption(id="00000000-0000-0000-0000-000000000201", label=_("North Bed")),
            ScopeOption(id="00000000-0000-0000-0000-000000000202", label=_("South Bed")),
            ScopeOption(id="00000000-0000-0000-0000-000000000203", label=_("Propagation")),
            ScopeOption(id="00000000-0000-0000-0000-000000000204", label=_("Herbs")),
        ]
        selected_group = groups[0]
        selected_greenhouse = greenhouses[0]
        selected_zone = zones[0]
        telemetry = {
            zones[0].id: {"temperature": 23.4, "air_humidity": 62, "soil_moisture": 48, "co2": 820, "light": 7200},
            zones[1].id: {"temperature": 29.2, "air_humidity": 51, "soil_moisture": 33, "co2": 760, "light": 6500},
            zones[2].id: {"temperature": 21.1, "air_humidity": 78, "soil_moisture": 70, "co2": 900, "light": 4200},
            zones[3].id: {"temperature": 24.5, "air_humidity": 58, "soil_moisture": 41, "co2": 790, "light": 5600},
        }
        plant_contexts = plant_context_by_zone([
            {"id": "demo-batch-1", "zone_id": zones[0].id, "name": _("Tomato Batch"), "species": _("Tomato"), "cultivar": "Roma", "growth_stage": _("Vegetative"), "planted_at": "2026-05-01"},
            {"id": "demo-batch-2", "zone_id": zones[2].id, "name": _("Seedlings"), "species": _("Mixed greens"), "growth_stage": _("Germination"), "planted_at": "2026-05-10"},
        ])
        commands = []

    def current_context():
        if not (selected_group and selected_greenhouse and selected_zone):
            return None
        return build_zone_context(
            group=selected_group,
            greenhouse=selected_greenhouse,
            zone=selected_zone,
            telemetry=telemetry,
            plant_contexts=plant_contexts,
            commands=commands,
        )

    def render_scope_status() -> None:
        scope_status.clear()
        with scope_status:
            if selected_group:
                ui.chip(selected_group.label, icon="groups").props("outline color=primary")
            if selected_greenhouse:
                ui.chip(selected_greenhouse.label, icon="yard").props("outline color=primary")
            if selected_zone:
                ui.chip(selected_zone.label, icon="location_on").props("outline color=secondary")
            if demo_mode:
                ui.chip(_("Demo data"), icon="science").props("outline color=orange")
            if not selected_group:
                ui.chip(_("No group selected"), icon="info").props("outline")
        render_mode_status()

    def render_mode_status() -> None:
        mode_status.clear()
        with mode_status:
            if demo_mode:
                ui.chip(_("Offline demo fallback"), icon="science").props("outline color=orange")
                return
            if control_mode_error:
                ui.chip(_("Control mode unavailable"), icon="warning").props("outline color=red")
                ui.label(control_mode_error).classes("text-xs text-red-600")
                return
            if not control_mode_loaded or control_mode is None:
                ui.chip(_("Loading control mode"), icon="hourglass_empty").props("outline")
                return
            label = _("MQTT remote control") if control_mode == "mqtt" else _("Simulator control")
            ui.chip(label, icon="settings_remote" if control_mode == "mqtt" else "precision_manufacturing").props("outline color=primary")
            if control_mode == "mqtt":
                ui.label(_("Approved commands are sent to the MQTT broker; physical device movement requires subscribed hardware.")).classes("text-xs opacity-70")
            elif not simulator_running:
                ui.label(_("Simulator mode is selected, but the simulator is not running. Start it on the simulator page before proposing commands.")).classes("text-xs text-amber-700")

    def render_map() -> None:
        map_area.clear()
        with map_area:
            if selected_group is None:
                empty_state(_("No group selected"), _("Select or create a greenhouse group before using the operator panel."), icon="groups")
                return
            if selected_greenhouse is None:
                empty_state(_("No greenhouse selected"), _("Select or create a greenhouse to show its zones."), icon="yard")
                return
            model = build_greenhouse_map_model(
                zones,
                selected_zone_id=selected_zone.id if selected_zone else None,
                pending_counts=pending_counts_by_zone(commands),
                telemetry_by_zone=telemetry,
            )
            render_greenhouse_map(model, on_select=select_zone)

    def render_drawer() -> None:
        drawer_area.clear()
        with drawer_area:
            disabled_reason = None
            controls_disabled = False
            if not demo_mode and not control_mode_loaded:
                controls_disabled = True
                disabled_reason = _("Control mode is still loading.")
            elif control_mode_error:
                controls_disabled = True
                disabled_reason = _("Control mode could not be loaded; proposals are disabled.")
            elif control_mode == "simulator" and not simulator_running:
                controls_disabled = True
                disabled_reason = _("Simulator is not running. Start it from the simulator page before proposing commands.")
            render_zone_control_drawer(
                current_context(),
                on_propose=queue_proposal,
                on_approve=lambda command_id: ui.timer(0, lambda: approve_command(command_id), once=True),
                on_reject=lambda command_id: ui.timer(0, lambda: reject_command(command_id), once=True),
                control_mode="demo" if demo_mode else control_mode,
                controls_disabled=controls_disabled,
                disabled_reason=disabled_reason,
            )

    def render_recent() -> None:
        recent_area.clear()
        completed = [command for command in commands if command.get("status") not in {"proposed", "validated", "approved"}]
        with recent_area:
            if not completed:
                empty_state(_("No recent completed commands"), _("Approved, rejected, failed, and expired commands will be listed here."), icon="history")
                return
            for command in completed[:8]:
                with ui.row().classes("greenhouse-card w-full items-center justify-between p-3 rounded"):
                    ui.label(f"{command.get('actuator_name', 'actuator')} → {command.get('action', 'unknown')}").classes("font-medium")
                    ui.badge(str(command.get("status", "unknown")), color="blue")

    def render_all() -> None:
        render_scope_status()
        render_map()
        render_drawer()
        render_recent()

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

    async def load_control_mode() -> None:
        nonlocal control_mode, control_mode_loaded, control_mode_error, simulator_running
        control_mode_loaded = False
        control_mode_error = None
        try:
            async with api_client(timeout=10.0) as client:
                settings_response = await client.get("/api/settings")
                if settings_response.status_code != 200:
                    control_mode = None
                    control_mode_error = _("Failed to load control mode: {error}", error=response_error(settings_response))
                    return
                control_mode = settings_response.json().get("control_mode") or "mqtt"
                if control_mode == "simulator":
                    status_response = await client.get("/api/simulator/status")
                    simulator_running = status_response.status_code == 200 and bool(status_response.json().get("running"))
                else:
                    simulator_running = False
                control_mode_loaded = True
        except httpx.HTTPError as exc:
            control_mode = None
            control_mode_error = _("Failed to load control mode: {error}", error=exc)
        finally:
            render_scope_status()

    async def load_groups() -> None:
        nonlocal groups, selected_group
        try:
            async with api_client(timeout=10.0) as client:
                response = await client.get("/api/groups")
            if response.status_code != 200:
                notify(_("Failed to load groups: {error}", error=response_error(response)), "negative")
                groups = []
                selected_group = None
                return
            groups = build_scope_options(response.json(), fallback_prefix=_("Group"))
            if not groups:
                enable_demo_mode()
                return
            selected_group = groups[0]
        except httpx.HTTPError as exc:
            notify(_("Failed to load groups: {error}", error=exc), "negative")
            groups = []
            selected_group = None
        finally:
            set_group_options()

    async def load_greenhouses() -> None:
        nonlocal greenhouses, selected_greenhouse, selected_zone, zones
        if demo_mode:
            set_greenhouse_options()
            return
        greenhouses = []
        zones = []
        selected_greenhouse = None
        selected_zone = None
        if selected_group is None:
            set_greenhouse_options()
            return
        try:
            async with api_client(timeout=10.0) as client:
                response = await client.get(f"/api/groups/{selected_group.id}/greenhouses")
            if response.status_code != 200:
                notify(_("Failed to load greenhouses: {error}", error=response_error(response)), "negative")
                return
            greenhouses = build_scope_options(response.json(), fallback_prefix=_("Greenhouse"))
            selected_greenhouse = greenhouses[0] if greenhouses else None
        except httpx.HTTPError as exc:
            notify(_("Failed to load greenhouses: {error}", error=exc), "negative")
        finally:
            set_greenhouse_options()

    async def load_panel_data() -> None:
        nonlocal zones, selected_zone, telemetry, plant_contexts, commands
        if demo_mode:
            render_all()
            return
        previous_zone_id = selected_zone.id if selected_zone else None
        zones = []
        telemetry = {}
        plant_contexts = {}
        commands = []
        if selected_group is None or selected_greenhouse is None:
            render_all()
            return

        try:
            async with api_client(timeout=10.0) as client:
                zones_response = await client.get(f"/api/groups/{selected_group.id}/greenhouses/{selected_greenhouse.id}/zones")
                commands_response = await client.get(f"/api/commands/groups/{selected_group.id}/recent")
                telemetry_response = await client.get(f"/api/groups/{selected_group.id}/telemetry/latest")
                plants_response = await client.get(f"/api/groups/{selected_group.id}/plant-batches")

            if zones_response.status_code != 200:
                notify(_("Failed to load zones: {error}", error=response_error(zones_response)), "negative")
                render_all()
                return

            zones = build_scope_options(zones_response.json(), fallback_prefix=_("Zone"))
            selected_zone = selected_or_first(zones, previous_zone_id)
            commands = commands_response.json() if commands_response.status_code == 200 else []
            telemetry_data = telemetry_response.json() if telemetry_response.status_code == 200 else {}
            telemetry_readings = telemetry_data.get("readings", []) if isinstance(telemetry_data, dict) else telemetry_data
            telemetry = telemetry_by_zone(telemetry_readings)
            plant_contexts = plant_context_by_zone(plants_response.json()) if plants_response.status_code == 200 else {}
        except httpx.HTTPError as exc:
            notify(_("Failed to load control data: {error}", error=exc), "negative")
        finally:
            render_all()

    async def refresh_commands() -> None:
        nonlocal commands
        if demo_mode or selected_group is None:
            return
        await load_control_mode()
        try:
            async with api_client(timeout=10.0) as client:
                response = await client.get(f"/api/commands/groups/{selected_group.id}/recent")
            if response.status_code == 200:
                commands = response.json()
                render_all()
        except httpx.HTTPError:
            pass

    def choose_group(label: str | None) -> None:
        nonlocal selected_group
        selected_group = option_by_id(groups, group_label_to_id.get(label or ""))
        ui.timer(0, reload_for_group, once=True)

    def choose_greenhouse(label: str | None) -> None:
        nonlocal selected_greenhouse
        selected_greenhouse = option_by_id(greenhouses, greenhouse_label_to_id.get(label or ""))
        ui.timer(0, load_panel_data, once=True)

    async def reload_for_group() -> None:
        await load_greenhouses()
        await load_panel_data()

    def select_zone(zone_id: str) -> None:
        nonlocal selected_zone
        selected_zone = option_by_id(zones, zone_id)
        render_all()

    def queue_proposal(payload: dict[str, object]) -> None:
        if not demo_mode:
            if not control_mode_loaded or control_mode_error:
                notify(_("Control mode is not available; proposal was not created."), "negative")
                return
            if control_mode == "simulator" and not simulator_running:
                notify(_("Start the simulator before creating simulator-mode proposals."), "warning")
                return
        ui.timer(0, lambda: propose_command(payload), once=True)

    async def propose_command(payload: dict[str, object]) -> None:
        nonlocal commands
        refresh_button.disable()
        if demo_mode:
            commands = [
                {
                    "id": str(uuid4()),
                    "group_id": payload.get("group_id"),
                    "greenhouse_id": payload.get("greenhouse_id"),
                    "zone_id": payload.get("zone_id"),
                    "actuator_name": payload.get("actuator"),
                    "action": payload.get("action"),
                    "value": payload.get("value"),
                    "duration_seconds": payload.get("duration_seconds"),
                    "source": "manual",
                    "reason": payload.get("reason"),
                    "validation_errors": None,
                    "status": "proposed",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                *commands,
            ]
            notify(_("Demo command proposed"), "positive")
            render_all()
            refresh_button.enable()
            return
        try:
            async with api_client(timeout=10.0) as client:
                response = await client.post("/api/commands/propose", json=payload)
            if response.status_code != 201:
                notify(_("Propose failed: {error}", error=response_error(response)), "negative")
                return
            notify(_("Command proposed"), "positive")
            await refresh_commands()
        except httpx.HTTPError as exc:
            notify(_("Propose failed: {error}", error=exc), "negative")
        finally:
            refresh_button.enable()

    async def approve_command(command_id: str) -> None:
        nonlocal commands
        if demo_mode:
            commands = [{**command, "status": "executed"} if str(command.get("id")) == command_id else command for command in commands]
            notify(_("Demo command approved"), "positive")
            render_all()
            return
        try:
            async with api_client(timeout=15.0) as client:
                response = await client.post(f"/api/commands/{command_id}/approve")
            if response.status_code != 200:
                notify(_("Approve failed: {error}", error=response_error(response)), "negative")
                return
            notify(_("Command approved"), "positive")
            await load_panel_data()
        except httpx.HTTPError as exc:
            notify(_("Approve failed: {error}", error=exc), "negative")

    async def reject_command(command_id: str) -> None:
        nonlocal commands
        if demo_mode:
            commands = [{**command, "status": "cancelled"} if str(command.get("id")) == command_id else command for command in commands]
            notify(_("Demo command rejected"), "warning")
            render_all()
            return
        try:
            async with api_client(timeout=10.0) as client:
                response = await client.post(f"/api/commands/{command_id}/cancel")
            if response.status_code != 200:
                notify(_("Reject failed: {error}", error=response_error(response)), "negative")
                return
            notify(_("Command rejected"), "warning")
            await refresh_commands()
        except httpx.HTTPError as exc:
            notify(_("Reject failed: {error}", error=exc), "negative")

    async def refresh_control_page() -> None:
        await load_control_mode()
        await reload_for_group()

    def schedule_refresh() -> None:
        if demo_mode:
            render_all()
            return
        ui.timer(0, refresh_control_page, once=True)

    await load_control_mode()
    await load_groups()
    await load_greenhouses()
    await load_panel_data()
    ui.timer(10, refresh_commands)


__all__ = ["control", "command_to_action"]
