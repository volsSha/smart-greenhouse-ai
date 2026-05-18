"""AI chat page with conversation management and tool transparency."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from nicegui import ui

from app.i18n.core import _
from app.ui.api_client import api_client, response_error
from app.ui.components.chat_message import (
    assistant_message_bubble,
    system_message,
    user_message_bubble,
)
from app.ui.components.design import empty_state, page_container, page_hero, section_card
from app.ui.components.proposed_action_card import proposed_action_card
from app.ui.components.tool_call_trace import tool_call_panel
from app.ui.layouts.main_layout import main_layout

logger = logging.getLogger(__name__)

ScopeLevel = Literal["group", "greenhouse", "zone"]


@dataclass
class ScopeOption:
    id: str
    label: str


@dataclass
class ChatScopeState:
    group_id: str | None = None
    greenhouse_id: str | None = None
    zone_id: str | None = None
    labels: dict[ScopeLevel, str] = field(default_factory=dict)
    unresolved: set[ScopeLevel] = field(default_factory=set)

    def clear(self) -> None:
        self.group_id = None
        self.greenhouse_id = None
        self.zone_id = None
        self.labels.clear()
        self.unresolved.clear()

    def select_group(self, group_id: str | None, label: str | None = None) -> None:
        self.group_id = group_id or None
        self.greenhouse_id = None
        self.zone_id = None
        self._set_label("group", self.group_id, label)
        self.labels.pop("greenhouse", None)
        self.labels.pop("zone", None)
        self.unresolved.discard("group")
        self.unresolved.discard("greenhouse")
        self.unresolved.discard("zone")

    def select_greenhouse(self, greenhouse_id: str | None, label: str | None = None) -> None:
        self.greenhouse_id = greenhouse_id or None
        self.zone_id = None
        self._set_label("greenhouse", self.greenhouse_id, label)
        self.labels.pop("zone", None)
        self.unresolved.discard("greenhouse")
        self.unresolved.discard("zone")

    def select_zone(self, zone_id: str | None, label: str | None = None) -> None:
        self.zone_id = zone_id or None
        self._set_label("zone", self.zone_id, label)
        self.unresolved.discard("zone")

    def rehydrate(
        self,
        group_id: str | None,
        greenhouse_id: str | None,
        zone_id: str | None,
        option_labels: dict[ScopeLevel, dict[str, str]],
    ) -> None:
        self.clear()
        values: dict[ScopeLevel, str | None] = {
            "group": group_id,
            "greenhouse": greenhouse_id,
            "zone": zone_id,
        }
        self.group_id = group_id
        self.greenhouse_id = greenhouse_id
        self.zone_id = zone_id
        for level, value in values.items():
            if not value:
                continue
            label = option_labels.get(level, {}).get(value)
            if label:
                self.labels[level] = label
            else:
                self.labels[level] = f"{_level_name(level)} {value[:8]}"
                self.unresolved.add(level)

    def can_send(self) -> bool:
        return not self.unresolved

    def to_dict(self) -> dict[str, str | None]:
        return _build_scope_dict(self.group_id, self.greenhouse_id, self.zone_id)

    def _set_label(self, level: ScopeLevel, value: str | None, label: str | None) -> None:
        if value:
            self.labels[level] = label or value[:8]
        else:
            self.labels.pop(level, None)


@dataclass
class ChatRenderState:
    selected_conversation_id: str | None = None
    load_token: int = 0
    send_token: int = 0

    def start_new(self) -> None:
        self.selected_conversation_id = None
        self.load_token += 1
        self.send_token += 1

    def select_conversation(self, conversation_id: str | None) -> int:
        self.selected_conversation_id = conversation_id
        self.load_token += 1
        return self.load_token

    def start_send(self) -> tuple[int, str | None]:
        self.send_token += 1
        return self.send_token, self.selected_conversation_id

    def load_is_current(self, token: int, conversation_id: str) -> bool:
        return self.load_token == token and self.selected_conversation_id == conversation_id

    def send_is_current(self, token: int, conversation_id: str | None) -> bool:
        return self.send_token == token and self.selected_conversation_id == conversation_id


def _build_scope_dict(
    group_id: str | None,
    greenhouse_id: str | None,
    zone_id: str | None,
) -> dict[str, str | None]:
    return {
        "group_id": group_id or None,
        "greenhouse_id": greenhouse_id or None,
        "zone_id": zone_id or None,
    }


def _option_label(name: str | None, option_id: str) -> str:
    base = (name or option_id[:8]).strip() or option_id[:8]
    return f"{base} · {option_id[:8]}"


def _option_maps(options: list[ScopeOption]) -> tuple[dict[str, str], dict[str, str]]:
    label_to_id = {_option_label(option.label, option.id): option.id for option in options}
    id_to_label = {value: label for label, value in label_to_id.items()}
    return label_to_id, id_to_label


def _level_name(level: ScopeLevel) -> str:
    return {"group": "Group", "greenhouse": "Greenhouse", "zone": "Zone"}[level]


_DEFAULTS: dict[str, Any] = {
    "observations": [],
    "recommendations": [],
    "proposed_actions": [],
}


def _parse_assistant_content(content: str) -> dict[str, Any]:
    """Parse persisted assistant JSON content into a structured dict."""
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {"summary": str(content) if content else "", **_DEFAULTS}

    if not isinstance(parsed, dict):
        return {"summary": str(content) if content else "", **_DEFAULTS}

    for key, default in _DEFAULTS.items():
        parsed.setdefault(key, default)
    return parsed


def _render_conversation_messages(
    messages: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    on_approve: Callable[[str], Any] | None = None,
    on_reject: Callable[[str], Any] | None = None,
) -> None:
    """Render all messages from a conversation into the chat area."""
    if not messages:
        empty_state(
            _("No messages yet"),
            _("Ask about greenhouse health, sensor anomalies, recent trends, or safe actuator actions."),
            icon="forum",
        )
        return

    tool_calls_by_idx: dict[int, list[dict[str, Any]]] = {}
    if tool_calls:
        assistant_indices = [i for i, m in enumerate(messages) if m.get("role") == "assistant"]
        if assistant_indices:
            tool_calls_by_idx[assistant_indices[0]] = tool_calls

    with ui.column().classes("w-full gap-4"):
        for idx, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            created_at = msg.get("created_at")

            if role == "user":
                user_message_bubble(content, timestamp=created_at)
            elif role == "assistant":
                parsed = _parse_assistant_content(content)
                assistant_message_bubble(
                    content=parsed.get("summary", content),
                    observations=parsed.get("observations", []),
                    recommendations=parsed.get("recommendations", []),
                    status=parsed.get("status", "ok"),
                    timestamp=created_at,
                )

                associated_tools = tool_calls_by_idx.get(idx, [])
                if associated_tools:
                    tool_call_panel(associated_tools)

                proposed_actions = parsed.get("proposed_actions", [])
                if proposed_actions:
                    with ui.column().classes("w-full gap-2 mt-2"):
                        ui.label(_("Proposed Actions")).classes("text-xs font-semibold opacity-60")
                        for action in proposed_actions:
                            proposed_action_card(action, on_approve=on_approve, on_reject=on_reject)
            elif role == "system":
                system_message(content)


@ui.page("/ai-chat")
async def ai_chat() -> None:
    """Render the AI chat page with conversation management."""
    main_layout()

    with page_container():
        page_hero(
            _("AI Assistant"),
            _("Ask scoped operational questions and review transparent tool calls before approving physical actions."),
            icon="smart_toy",
            meta=_("Intelligence"),
        )

    render_state = ChatRenderState()
    scope_state = ChatScopeState()
    is_processing: dict[str, bool] = {"value": False}
    conversation_label_to_id: dict[str, str] = {}
    option_labels: dict[ScopeLevel, dict[str, str]] = {"group": {}, "greenhouse": {}, "zone": {}}
    option_label_to_id: dict[ScopeLevel, dict[str, str]] = {"group": {}, "greenhouse": {}, "zone": {}}
    selector_errors: dict[ScopeLevel, str | None] = {"group": None, "greenhouse": None, "zone": None}

    with page_container():
        with section_card(_("Conversation Context"), _("Select a saved thread or start a fresh all-greenhouses chat."), icon="hub"):
            with ui.row().classes("w-full gap-4 mt-4 items-center flex-wrap"):
                conversation_select = ui.select(
                    label=_("Conversation"),
                    options=[],
                    on_change=lambda e: select_conversation(e.value),
                ).classes("flex-1 min-w-[220px]")
                ui.button(_("New Conversation"), icon="add", on_click=lambda: start_new_conversation()).props("flat color=primary")

        with section_card(_("Operator Chat"), _("Responses include observations, recommendations, proposed actions, and tool traces."), icon="forum"):
            chat_area = ui.column().classes("greenhouse-chat-panel w-full gap-4 mt-4 flex-1 overflow-y-auto")
            chat_area.style("max-height: 60vh; min-height: 340px;")

            loading_container = ui.column().classes("w-full items-center gap-2 mt-4")
            loading_container.set_visibility(False)
            error_container = ui.column().classes("w-full mt-4")
            error_container.set_visibility(False)

            with ui.column().classes("w-full gap-2 mt-4"):
                scope_status = ui.row().classes("items-center gap-2 flex-wrap")
                scope_error = ui.label().classes("text-xs text-red-500")
                with ui.row().classes("w-full gap-2 flex-wrap"):
                    group_select = ui.select(label=_("Group"), options=[], on_change=lambda e: choose_group(e.value)).classes("min-w-[180px]")
                    greenhouse_select = ui.select(label=_("Greenhouse"), options=[], on_change=lambda e: choose_greenhouse(e.value)).classes("min-w-[180px]")
                    zone_select = ui.select(label=_("Zone"), options=[], on_change=lambda e: choose_zone(e.value)).classes("min-w-[180px]")
                    ui.button(_("Clear scope"), icon="close", on_click=lambda: clear_scope()).props("flat size=sm aria-label='Clear scope'")

            with ui.row().classes("greenhouse-composer w-full gap-2 mt-4 items-end sticky bottom-0 p-3"):
                message_input = ui.textarea(placeholder=_("Ask about your greenhouses...")).classes("flex-1").props("rows=1 autogrow outlined dense")
                send_button = ui.button(_("Send"), icon="send", on_click=lambda: send_message()).props("color=primary")

    def render_scope_status() -> None:
        scope_status.clear()
        with scope_status:
            if not any([scope_state.group_id, scope_state.greenhouse_id, scope_state.zone_id]):
                ui.chip(_("All-greenhouses chat"), icon="public").props("outline")
            for level in ("group", "greenhouse", "zone"):
                value = getattr(scope_state, f"{level}_id")
                if not value:
                    continue
                label = scope_state.labels.get(level, value[:8])
                color = "warning" if level in scope_state.unresolved else "primary"
                ui.chip(label, icon="warning" if level in scope_state.unresolved else "check").props(f"outline color={color}")
        unresolved = bool(scope_state.unresolved)
        scope_error.text = _("Saved scope contains unavailable entities. Clear or reselect scope before sending.") if unresolved else ""

    def update_selector_enabled() -> None:
        greenhouse_select.set_enabled(bool(scope_state.group_id))
        zone_select.set_enabled(bool(scope_state.greenhouse_id))

    def apply_scope_values() -> None:
        group_select.set_value(option_labels["group"].get(scope_state.group_id or ""))
        greenhouse_select.set_value(option_labels["greenhouse"].get(scope_state.greenhouse_id or ""))
        zone_select.set_value(option_labels["zone"].get(scope_state.zone_id or ""))
        update_selector_enabled()
        render_scope_status()

    async def load_conversations() -> None:
        try:
            async with api_client(timeout=10.0) as client:
                resp = await client.get("/api/ai/conversations")
                resp.raise_for_status()
                conversations = resp.json()

            conversation_label_to_id.clear()
            options: list[str] = []
            for conv in conversations:
                conv_id = str(conv.get("id", ""))
                title = conv.get("title") or conv_id[:8]
                label = _option_label(title, conv_id)
                conversation_label_to_id[label] = conv_id
                options.append(label)
            conversation_select.set_options(options)
        except httpx.HTTPError:
            logger.warning("Failed to load conversations", exc_info=True)

    async def load_scope_options(level: ScopeLevel, url: str) -> None:
        selector_errors[level] = None
        try:
            async with api_client(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                rows = resp.json()
        except httpx.HTTPError as exc:
            selector_errors[level] = response_error(exc.response) if isinstance(exc, httpx.HTTPStatusError) else str(exc)
            rows = []

        options = [ScopeOption(id=str(row.get("id", "")), label=row.get("name") or str(row.get("id", ""))[:8]) for row in rows if row.get("id")]
        label_to_id, id_to_label = _option_maps(options)
        option_label_to_id[level] = label_to_id
        option_labels[level] = id_to_label
        target = {"group": group_select, "greenhouse": greenhouse_select, "zone": zone_select}[level]
        target.set_options(list(label_to_id.keys()))
        if selector_errors[level]:
            scope_error.text = selector_errors[level] or ""

    def label_value(level: ScopeLevel, label: str | None) -> tuple[str | None, str | None]:
        return option_label_to_id[level].get(label or ""), label

    async def _load_greenhouses_for_selected_group() -> None:
        option_labels["greenhouse"] = {}
        option_labels["zone"] = {}
        option_label_to_id["greenhouse"] = {}
        option_label_to_id["zone"] = {}
        greenhouse_select.set_options([])
        zone_select.set_options([])
        if scope_state.group_id:
            await load_scope_options("greenhouse", f"/api/groups/{scope_state.group_id}/greenhouses")
        update_selector_enabled()

    async def _load_zones_for_selected_greenhouse() -> None:
        option_labels["zone"] = {}
        option_label_to_id["zone"] = {}
        zone_select.set_options([])
        if scope_state.group_id and scope_state.greenhouse_id:
            await load_scope_options("zone", f"/api/groups/{scope_state.group_id}/greenhouses/{scope_state.greenhouse_id}/zones")
        update_selector_enabled()

    async def load_dependent_scope_options(
        group_id: str | None,
        greenhouse_id: str | None,
        conversation_id: str,
        token: int,
    ) -> bool:
        option_labels["greenhouse"] = {}
        option_labels["zone"] = {}
        option_label_to_id["greenhouse"] = {}
        option_label_to_id["zone"] = {}
        greenhouse_select.set_options([])
        zone_select.set_options([])
        if group_id:
            await load_scope_options("greenhouse", f"/api/groups/{group_id}/greenhouses")
            if not render_state.load_is_current(token, conversation_id):
                return False
        if group_id and greenhouse_id:
            await load_scope_options("zone", f"/api/groups/{group_id}/greenhouses/{greenhouse_id}/zones")
            if not render_state.load_is_current(token, conversation_id):
                return False
        return True

    def choose_group(label: str | None) -> None:
        value, display = label_value("group", label)
        scope_state.select_group(value, display)
        apply_scope_values()
        ui.timer(0, _load_greenhouses_for_selected_group, once=True)

    def choose_greenhouse(label: str | None) -> None:
        value, display = label_value("greenhouse", label)
        scope_state.select_greenhouse(value, display)
        apply_scope_values()
        ui.timer(0, _load_zones_for_selected_greenhouse, once=True)

    def choose_zone(label: str | None) -> None:
        value, display = label_value("zone", label)
        scope_state.select_zone(value, display)
        apply_scope_values()

    def clear_scope() -> None:
        scope_state.clear()
        greenhouse_select.set_options([])
        zone_select.set_options([])
        apply_scope_values()

    async def _approve_command(command_id: str) -> None:
        try:
            async with api_client(timeout=15.0) as client:
                resp = await client.post(f"/api/commands/{command_id}/approve")
                resp.raise_for_status()
            ui.notify(_("Command approved and executed"), type="positive")
        except httpx.HTTPError as exc:
            detail = response_error(exc.response) if isinstance(exc, httpx.HTTPStatusError) else str(exc)
            ui.notify(_("Approval failed: {detail}", detail=detail), type="negative")
            logger.warning("Command %s approval failed: %s", command_id, exc)

    async def _reject_command(command_id: str) -> None:
        try:
            async with api_client(timeout=15.0) as client:
                resp = await client.post(f"/api/commands/{command_id}/cancel")
                resp.raise_for_status()
            ui.notify(_("Command rejected"), type="warning")
        except httpx.HTTPError as exc:
            detail = response_error(exc.response) if isinstance(exc, httpx.HTTPStatusError) else str(exc)
            ui.notify(_("Rejection failed: {detail}", detail=detail), type="negative")
            logger.warning("Command %s rejection failed: %s", command_id, exc)

    async def load_conversation_messages(conversation_id: str, token: int) -> None:
        if not render_state.load_is_current(token, conversation_id):
            return
        chat_area.clear()
        try:
            async with api_client(timeout=10.0) as client:
                detail_resp, tools_resp = await asyncio.gather(
                    client.get(f"/api/ai/conversations/{conversation_id}"),
                    client.get(f"/api/ai/tool-calls/{conversation_id}"),
                )
                detail_resp.raise_for_status()
                tools_resp.raise_for_status()
                detail = detail_resp.json()
                tool_calls = tools_resp.json()

            if not render_state.load_is_current(token, conversation_id):
                return
            group_id = detail.get("group_id")
            greenhouse_id = detail.get("greenhouse_id")
            zone_id = detail.get("zone_id")
            if not await load_dependent_scope_options(group_id, greenhouse_id, conversation_id, token):
                return
            scope_state.rehydrate(group_id, greenhouse_id, zone_id, option_labels)
            apply_scope_values()
            _render_conversation_messages(
                detail.get("messages", []),
                tool_calls,
                on_approve=lambda cid: _approve_command(cid),
                on_reject=lambda cid: _reject_command(cid),
            )
        except httpx.HTTPError as exc:
            if render_state.load_is_current(token, conversation_id):
                ui.label(_("Error loading conversation: {error}", error=exc)).classes("text-red-500 text-sm")

    def select_conversation(label: str | None) -> None:
        conversation_id = conversation_label_to_id.get(label or "")
        token = render_state.select_conversation(conversation_id)
        loading_container.clear()
        loading_container.set_visibility(False)
        error_container.clear()
        error_container.set_visibility(False)
        if conversation_id:
            ui.timer(0.1, lambda: load_conversation_messages(conversation_id, token), once=True)

    def start_new_conversation() -> None:
        render_state.start_new()
        conversation_select.set_value(None)
        chat_area.clear()
        clear_scope()
        _render_conversation_messages([], [])

    async def refresh_visible_conversation(
        persisted_conversation_id: str,
        token: int,
        original_conversation_id: str | None,
    ) -> None:
        if not render_state.send_is_current(token, original_conversation_id):
            return
        render_state.selected_conversation_id = persisted_conversation_id
        load_token = render_state.load_token + 1
        render_state.load_token = load_token
        await load_conversation_messages(persisted_conversation_id, load_token)

    async def send_message() -> None:
        if is_processing["value"]:
            return
        content = message_input.value
        if not content or not content.strip():
            return
        if not scope_state.can_send():
            ui.notify(_("Clear or reselect unavailable scope before sending"), type="warning")
            return

        send_token, target_conversation_id = render_state.start_send()
        is_processing["value"] = True
        send_button.disable()
        message_input.set_value("")
        loading_container.clear()
        error_container.clear()
        error_container.set_visibility(False)

        if render_state.send_is_current(send_token, target_conversation_id):
            with chat_area:
                user_message_bubble(content.strip())
            loading_container.set_visibility(True)
            with loading_container:
                ui.spinner("dots", size="2rem")
                ui.label(_("Thinking...")).classes("text-sm opacity-50")

        try:
            payload: dict[str, Any] = {"message": content.strip(), "scope": scope_state.to_dict()}
            if target_conversation_id:
                payload["conversation_id"] = target_conversation_id

            async with api_client(timeout=60.0) as client:
                resp = await client.post("/api/ai/chat", json=payload)
                resp.raise_for_status()
                ai_response = resp.json()

            await load_conversations()
            persisted_conversation_id = ai_response.get("conversation_id") or target_conversation_id
            if persisted_conversation_id and render_state.send_is_current(send_token, target_conversation_id):
                loading_container.clear()
                loading_container.set_visibility(False)
                await refresh_visible_conversation(
                    persisted_conversation_id,
                    send_token,
                    target_conversation_id,
                )
        except httpx.HTTPError as exc:
            if render_state.send_is_current(send_token, target_conversation_id):
                loading_container.clear()
                loading_container.set_visibility(False)
                error_container.clear()
                error_container.set_visibility(True)
                with error_container:
                    ui.label(_("Request failed")).classes("text-red-500 font-semibold")
                    detail = response_error(exc.response) if isinstance(exc, httpx.HTTPStatusError) else str(exc)
                    ui.label(detail).classes("text-sm text-red-400")
                    ui.button(_("Retry"), icon="refresh", on_click=lambda: send_message()).props("flat color=red size=sm")
            logger.error("AI chat request failed: %s", exc)
        finally:
            is_processing["value"] = False
            send_button.enable()

    await load_conversations()
    await load_scope_options("group", "/api/groups")
    update_selector_enabled()
    render_scope_status()
    _render_conversation_messages([], [])
