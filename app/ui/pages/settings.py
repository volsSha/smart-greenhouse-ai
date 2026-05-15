"""Settings page -- model selection and OpenRouter catalog management."""

from __future__ import annotations

import logging
import httpx
from datetime import datetime
from nicegui import ui

from app.i18n.core import _
from app.ui.api_client import api_client, response_error
from app.ui.components.design import page_container, page_hero, section_card
from app.ui.layouts.main_layout import main_layout

logger = logging.getLogger(__name__)


@ui.page("/settings")
async def settings_page() -> None:
    """Render the system settings page with model catalog management."""
    main_layout()

    with page_container():
        page_hero(
            _("Model Settings"),
            _("Configure the AI chat model and manage the OpenRouter model catalog."),
            icon="settings",
            meta=_("System"),
        )

        current_card = section_card(_("Current Settings"), _("Active chat and embedding model state."), icon="tune")
    with current_card:
        settings_container = ui.column().classes("greenhouse-card w-full gap-3 p-4 mt-4")
        settings_loading = ui.column().classes("w-full items-center gap-2")
        with settings_loading:
            ui.spinner("dots")
            ui.label(_("Loading settings...")).classes("text-sm opacity-60")

        with ui.column().classes("w-full gap-2 mt-4"):
            ui.label(_("Embedding Model")).classes("text-sm font-semibold")
            ui.label(
                _(
                    "The embedding model is fixed by configuration. "
                    "Changing it requires reindexing all RAG documents."
                )
            ).classes("text-xs text-amber-600 opacity-80")
            embedding_info = ui.label(_("Loading...")).classes("text-sm opacity-70")

        control_card = section_card(_("Control Mode"), _("Choose where approved greenhouse commands execute."), icon="toggle_on")
    with control_card:
        with ui.column().classes("greenhouse-card w-full gap-3 p-4 mt-4"):
            control_mode_labels = {
                _("MQTT remote devices"): "mqtt",
                _("Internal simulator"): "simulator",
            }
            control_mode_value_to_label = {value: label for label, value in control_mode_labels.items()}
            ui.label(_("MQTT mode sends approved commands to subscribed remote devices. Simulator mode changes the internal simulator state.")).classes("text-xs opacity-70")
            with ui.row().classes("w-full gap-3 items-end flex-wrap"):
                control_mode_select = ui.select(
                    label=_("Control Mode"),
                    options=list(control_mode_labels),
                ).classes("min-w-[260px]")
                save_control_mode_button = ui.button(
                    _("Save Control Mode"),
                    icon="save",
                    on_click=lambda: save_control_mode(),
                ).props("color=primary")
            control_mode_status = ui.label(_("Loading...")).classes("text-sm opacity-70")

    # --- Model Catalog Section ---
    with page_container():
        catalog_card = section_card(_("OpenRouter Model Catalog"), _("Search, refresh, and choose the model used by AI chat."), icon="view_list")
    with catalog_card:
        with ui.row().classes("w-full gap-3 items-center flex-wrap mt-4"):
            search_input = ui.input(
                placeholder=_("Search models..."),
                on_change=lambda: refresh_catalog_display(),
            ).classes("flex-1 min-w-[200px]").props("debounce=300")

            provider_filter = ui.select(
                label=_("Provider"),
                options={_("All"): None},
                on_change=lambda: refresh_catalog_display(),
            ).classes("w-40")

            capability_filter = ui.select(
                label=_("Capability"),
                options={_("All"): None},
                on_change=lambda: refresh_catalog_display(),
            ).classes("w-40")

            refresh_button = ui.button(
                _("Refresh Catalog"),
                icon="refresh",
                on_click=lambda: refresh_catalog_from_api(),
            ).props("color=primary")

        status_container = ui.column().classes("w-full mt-2")

        catalog_table = ui.aggrid(
            {
                "columnDefs": [
                    {"headerName": _("Model"), "field": "name", "flex": 2},
                    {"headerName": _("Provider"), "field": "provider", "flex": 1},
                    {"headerName": _("Prompt $/M"), "field": "prompt_price", "flex": 1},
                    {"headerName": _("Completion $/M"), "field": "completion_price", "flex": 1},
                    {"headerName": _("Context"), "field": "context_length", "flex": 1},
                ],
                "rowData": [],
                "defaultColDef": {"sortable": True, "filter": True, "resizable": True},
            },
            html_columns=[0],
        ).classes("w-full mt-4").style("height: 400px;")

        with ui.row().classes("w-full gap-2 mt-2 items-end flex-wrap"):
            model_select = ui.select(
                label=_("Model"),
                options=[],
                on_change=lambda event: select_model(event.value),
            ).classes("min-w-[320px] flex-1")
            ui.label(_("Selected:")).classes("text-sm opacity-60")
            selected_model_label = ui.label(_("None")).classes("text-sm font-medium")
            save_model_button = ui.button(
                _("Use Selected Model"),
                icon="check",
                on_click=lambda: select_current_model(),
            ).props("color=positive")
            save_model_button.disable()

    # --- State ---
    catalog_state: dict = {
        "models": [],
        "model_labels": {},
        "selected_model_id": None,
        "pending_model_id": None,
        "embedding_model": None,
        "embedding_dimension": None,
        "control_mode": "mqtt",
    }

    # --- Functions ---

    async def load_settings() -> None:
        """Load current settings from the API."""
        settings_loading.clear()
        try:
            async with api_client(timeout=10.0) as client:
                resp = await client.get("/api/settings")
                resp.raise_for_status()
                settings_data = resp.json()

            catalog_state["selected_model_id"] = settings_data.get("selected_chat_model")
            catalog_state["embedding_model"] = settings_data.get("embedding_model")
            catalog_state["embedding_dimension"] = settings_data.get("embedding_dimension")
            catalog_state["control_mode"] = settings_data.get("control_mode") or "mqtt"

            # Update UI
            settings_container.clear()
            with settings_container:
                with ui.row().classes("w-full gap-4 items-center"):
                    ui.label(_("Chat Model:")).classes("text-sm font-medium")
                    selected_label = ui.label(
                        settings_data.get("selected_chat_model") or _("Not selected")
                    ).classes("text-sm")
                    if not settings_data.get("selected_model_available"):
                        selected_label.classes("text-sm text-red-500")
                        ui.label(_("(Unavailable)")).classes("text-xs text-red-500")

                ui.label(
                    _("Last refresh: {timestamp}", timestamp=format_timestamp(settings_data.get('last_refresh_at')))
                ).classes("text-xs opacity-60")

                refresh_status = settings_data.get("last_refresh_status")
                if refresh_status == "failed":
                    ui.label(
                        _(
                            "Refresh failed: {error}",
                            error=settings_data.get('last_refresh_error', _('Unknown error')),
                        )
                    ).classes("text-xs text-red-500")

            # Update embedding info
            embedding_info.text = _(
                "{model} ({dimension} dimensions)",
                model=catalog_state['embedding_model'] or _('Not configured'),
                dimension=catalog_state['embedding_dimension'] or '?',
            )

            selected_model_label.text = settings_data.get("selected_chat_model") or _("None")
            control_mode = catalog_state["control_mode"]
            control_mode_select.set_value(control_mode_value_to_label.get(control_mode))
            control_mode_status.text = _("Saved: {mode}", mode=control_mode.upper())

        except httpx.HTTPError as exc:
            logger.error("Failed to load settings: %s", exc)
            settings_container.clear()
            with settings_container:
                ui.label(_("Failed to load settings")).classes("text-red-500 text-sm")

    async def load_catalog() -> None:
        """Load the model catalog from the API."""
        search = search_input.value or None
        provider = provider_filter.value or None
        capability = capability_filter.value or None

        try:
            params = {}
            if search:
                params["search"] = search
            if provider:
                params["provider"] = provider
            if capability:
                params["capability"] = capability

            async with api_client(timeout=10.0) as client:
                resp = await client.get("/api/settings/catalog", params=params)
                resp.raise_for_status()
                models = resp.json()

            catalog_state["models"] = models
            update_catalog_table(models)

        except httpx.HTTPError as exc:
            logger.error("Failed to load catalog: %s", exc)
            update_catalog_table([])

    def update_catalog_table(models: list) -> None:
        """Update the AG Grid table with model data."""
        row_data = []
        model_options: list[str] = []
        model_labels: dict[str, str] = {}
        selected_label = None

        for m in models:
            model_id = m.get("model_id", "")
            label = f"{m.get('name', model_id)} ({model_id})"
            prompt_price = m.get("prompt_price_per_million")
            completion_price = m.get("completion_price_per_million")

            if model_id:
                model_options.append(label)
                model_labels[label] = model_id
                if model_id == catalog_state.get("pending_model_id") or model_id == catalog_state.get("selected_model_id"):
                    selected_label = label

            row_data.append({
                "name": m.get("name", model_id),
                "provider": m.get("provider", ""),
                "prompt_price": f"${prompt_price:.2f}" if prompt_price else "N/A",
                "completion_price": f"${completion_price:.2f}" if completion_price else "N/A",
                "context_length": format_context_length(m.get("context_length")),
            })

        catalog_state["model_labels"] = model_labels
        model_select.set_options(model_options)
        if selected_label:
            model_select.set_value(selected_label)

        catalog_table.options["rowData"] = row_data
        catalog_table.update()

    def select_model(value: object) -> None:
        model_id = catalog_state["model_labels"].get(str(value))
        catalog_state["pending_model_id"] = model_id
        save_model_button.set_enabled(bool(model_id))
        selected_model_label.text = model_id or catalog_state.get("selected_model_id") or _("None")

    async def refresh_catalog_from_api() -> None:
        """Refresh the catalog from OpenRouter API."""
        status_container.clear()
        with status_container:
            ui.spinner("dots", size="1rem")
            ui.label(_("Refreshing catalog...")).classes("text-sm opacity-60")

        refresh_button.disable()

        try:
            async with api_client(timeout=60.0) as client:
                resp = await client.post("/api/settings/catalog/refresh")
                resp.raise_for_status()
                result = resp.json()

            status_container.clear()
            with status_container:
                if result.get("status") == "success":
                    ui.icon("check_circle", color="positive").classes("text-sm")
                    ui.label(
                        _(
                            "Catalog refreshed: {count} models loaded",
                            count=result.get('models_added', 0),
                        )
                    ).classes("text-sm text-green-600")
                else:
                    ui.icon("error", color="negative").classes("text-sm")
                    ui.label(
                        result.get("message") or _("Refresh failed")
                    ).classes("text-sm text-red-500")

            # Reload settings and catalog
            await load_settings()
            await load_catalog()

        except httpx.HTTPError as exc:
            status_container.clear()
            with status_container:
                ui.icon("error", color="negative").classes("text-sm")
                ui.label(_("Refresh failed: {error}", error=response_error(exc.response))).classes("text-sm text-red-500")
                ui.button(
                    _("Retry"),
                    icon="refresh",
                    on_click=lambda: refresh_catalog_from_api(),
                ).props("flat color=red size=sm")

        finally:
            refresh_button.enable()

    async def refresh_catalog_display() -> None:
        """Refresh the catalog display with current filters."""
        await load_catalog()

    async def select_current_model() -> None:
        """Persist the selected model as the chat model."""
        model_id = catalog_state.get("pending_model_id")
        if not model_id:
            ui.notify(_("Select a model first"), type="warning")
            return

        save_model_button.disable()
        try:
            async with api_client(timeout=10.0) as client:
                resp = await client.put("/api/settings", json={"selected_chat_model": model_id})
                resp.raise_for_status()

            catalog_state["selected_model_id"] = model_id
            selected_model_label.text = model_id
            ui.notify(_("Chat model saved"), type="positive")
            await load_settings()
        except httpx.HTTPError as exc:
            ui.notify(_("Failed to save model: {error}", error=response_error(exc)), type="negative")
            save_model_button.enable()

    async def save_control_mode() -> None:
        label = str(control_mode_select.value or "")
        control_mode = control_mode_labels.get(label)
        if control_mode is None:
            ui.notify(_("Select a control mode first"), type="warning")
            return

        save_control_mode_button.disable()
        try:
            async with api_client(timeout=10.0) as client:
                resp = await client.put("/api/settings/control-mode", json={"control_mode": control_mode})
                resp.raise_for_status()
                settings_data = resp.json()

            catalog_state["control_mode"] = settings_data.get("control_mode") or control_mode
            control_mode_status.text = _("Saved: {mode}", mode=catalog_state["control_mode"].upper())
            ui.notify(_("Control mode saved"), type="positive")
        except httpx.HTTPError as exc:
            previous = catalog_state.get("control_mode") or "mqtt"
            control_mode_select.set_value(control_mode_value_to_label.get(previous))
            ui.notify(_("Failed to save control mode: {error}", error=response_error(exc)), type="negative")
        finally:
            save_control_mode_button.enable()

    def format_timestamp(ts: str | None) -> str:
        """Format a timestamp for display."""
        if not ts:
            return _("Never")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            return _("Unknown")

    def format_context_length(length: int | None) -> str:
        """Format context length for display."""
        if not length:
            return "N/A"
        if length >= 1_000_000:
            return f"{length / 1_000_000:.1f}M"
        if length >= 1_000:
            return f"{length / 1_000:.0f}K"
        return str(length)

    # --- Initial load ---
    await load_settings()
    await load_catalog()
