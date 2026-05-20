"""AI chat page with conversation management and tool transparency."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from nicegui import app, ui

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
    return {"group": _("Group"), "greenhouse": _("Greenhouse"), "zone": _("Zone")}[level]


def _strip_option_id(label: str) -> str:
    return label.rsplit(" · ", 1)[0]


def _scope_parts(scope: ChatScopeState) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    for level in ("group", "greenhouse", "zone"):
        value = getattr(scope, f"{level}_id")
        if value:
            parts.append((_level_name(level), _strip_option_id(scope.labels.get(level, value[:8]))))
    return parts


def _scope_note(scope: ChatScopeState) -> str:
    parts = _scope_parts(scope)
    if not parts:
        return _("Sent to: All greenhouses")
    return _("Sent to: {scope}", scope=" / ".join(f"{name}: {label}" for name, label in parts))


def _scope_context_note(scope: ChatScopeState) -> str:
    parts = _scope_parts(scope)
    if not parts:
        return _("Scope: All greenhouses")
    return _("Scope: {scope}", scope=" / ".join(f"{name}: {label}" for name, label in parts))


def _prompt_templates() -> list[tuple[str, str, str]]:
    return [
        ("analytics", _("Current status"), _("Check current status for the selected greenhouse scope.")),
        ("today", _("Daily report"), _("Create a daily report for the selected greenhouse scope.")),
        ("warning", _("Issues and anomalies"), _("Find issues and anomalies in the selected greenhouse scope.")),
        ("water_drop", _("Irrigation advice"), _("Recommend irrigation changes for the selected greenhouse scope.")),
        ("task_alt", _("Action plan"), _("Create a safe action plan for the selected greenhouse scope.")),
    ]


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
    scope_note: str | None = None,
    on_approve: Callable[[str], Any] | None = None,
    on_reject: Callable[[str], Any] | None = None,
) -> None:
    """Render all messages from a conversation into the chat area."""
    if not messages:
        with ui.column().classes("w-full h-full min-h-[260px] items-center justify-center"):
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
                user_message_bubble(content, timestamp=created_at, scope_note=scope_note)
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

    last_conversation_key = "ai_chat_selected_conversation_id"
    render_state = ChatRenderState(
        selected_conversation_id=app.storage.user.get(last_conversation_key),
    )
    scope_state = ChatScopeState()
    is_processing: dict[str, bool] = {"value": False}
    conversation_label_to_id: dict[str, str] = {}
    conversation_id_to_label: dict[str, str] = {}
    option_labels: dict[ScopeLevel, dict[str, str]] = {"group": {}, "greenhouse": {}, "zone": {}}
    option_label_to_id: dict[ScopeLevel, dict[str, str]] = {"group": {}, "greenhouse": {}, "zone": {}}
    selector_errors: dict[ScopeLevel, str | None] = {"group": None, "greenhouse": None, "zone": None}

    with page_container():
        with section_card(_("Operator Chat"), _("Open a saved thread or continue the current scoped conversation in one workspace."), icon="forum"):
            with ui.row().classes("w-full gap-3 mt-4 items-center flex-wrap"):
                conversation_select = ui.select(
                    label=_("Chat history"),
                    options=[],
                    on_change=lambda e: select_conversation(e.value),
                ).classes("flex-1 min-w-[220px]").props("outlined dense")
                delete_conversation_button = ui.button(_("Delete"), icon="delete", on_click=lambda: open_delete_dialog()).props("flat color=negative")
                ui.button(_("New Conversation"), icon="add", on_click=lambda: start_new_conversation()).props("flat color=primary")

            with ui.column().classes("w-full gap-2 mt-4"):
                scope_status = ui.row().classes("items-center gap-2 flex-wrap")
                scope_error = ui.label().classes("text-xs text-red-500")
                with ui.row().classes("w-full gap-2 flex-wrap"):
                    group_select = ui.select(label=_("Group"), options=[], on_change=lambda e: choose_group(e.value)).classes("min-w-[180px]").props("outlined dense")
                    greenhouse_select = ui.select(label=_("Greenhouse"), options=[], on_change=lambda e: choose_greenhouse(e.value)).classes("min-w-[180px]").props("outlined dense")
                    zone_select = ui.select(label=_("Zone"), options=[], on_change=lambda e: choose_zone(e.value)).classes("min-w-[180px]").props("outlined dense")
                    clear_scope_button = ui.button(_("Clear scope"), icon="close", on_click=lambda: clear_scope()).props("flat size=sm aria-label='Clear scope'")

            with ui.row().classes("w-full gap-4 mt-4 items-stretch flex-wrap"):
                chat_area = ui.column().classes("greenhouse-chat-panel gap-4 flex-1 min-w-[320px] overflow-y-auto p-4")
                chat_area.style("max-height: 62vh; min-height: 380px;")

                with ui.column().classes("w-full lg:w-80 gap-3"):
                    ideas_panel = ui.column().classes("w-full gap-2 greenhouse-card p-3")

            loading_container = ui.column().classes("w-full items-center gap-2 mt-4")
            loading_container.set_visibility(False)
            error_container = ui.column().classes("w-full mt-4")
            error_container.set_visibility(False)

            with ui.column().classes("greenhouse-composer w-full gap-3 mt-4 sticky bottom-0 p-3"):
                composer_scope = ui.row().classes("items-center gap-2 flex-wrap")
                template_buttons = ui.row().classes("items-center gap-2 flex-wrap")
                with ui.row().classes("w-full gap-2 items-end"):
                    message_input = ui.textarea(placeholder=_("Ask about your greenhouses...")).classes("flex-1").props("rows=1 autogrow outlined dense")
                    send_button = ui.button(_("Send"), icon="send", on_click=lambda: send_message()).props("color=primary")

    def render_scope_chips(container: Any, compact: bool = False) -> None:
        container.clear()
        with container:
            if compact:
                ui.label(_("Send target")).classes("text-xs font-semibold opacity-60")
            if not any([scope_state.group_id, scope_state.greenhouse_id, scope_state.zone_id]):
                ui.chip(_("All greenhouses"), icon="public").props("outline")
            for level in ("group", "greenhouse", "zone"):
                value = getattr(scope_state, f"{level}_id")
                if not value:
                    continue
                label = _strip_option_id(scope_state.labels.get(level, value[:8]))
                color = "warning" if level in scope_state.unresolved else "primary"
                ui.chip(f"{_level_name(level)}: {label}", icon="warning" if level in scope_state.unresolved else "check").props(f"outline color={color}")

    def render_scope_status() -> None:
        render_scope_chips(scope_status)
        render_scope_chips(composer_scope, compact=True)
        unresolved = bool(scope_state.unresolved)
        scope_error.text = _("Saved scope contains unavailable entities. Clear or reselect scope before sending.") if unresolved else ""

    def render_templates() -> None:
        template_buttons.clear()
        with template_buttons:
            ui.label(_("Prompt templates")).classes("text-xs font-semibold opacity-60")
            for icon, label, prompt in _prompt_templates():
                ui.button(label, icon=icon, on_click=lambda p=prompt: message_input.set_value(p)).props("outline size=sm")

    def render_ideas(messages: list[dict[str, Any]] | None = None, note: str | None = None) -> None:
        ideas_panel.clear()
        with ideas_panel:
            ui.label(_("Follow-up ideas")).classes("text-sm font-semibold")
            ui.label(_("Suggestions from the assistant that you can send as your next message.")).classes("text-xs opacity-60")
            collected: list[tuple[str, str]] = []
            for msg in messages or []:
                if msg.get("role") != "assistant":
                    continue
                parsed = _parse_assistant_content(str(msg.get("content", "")))
                for recommendation in parsed.get("recommendations", []) or []:
                    collected.append((_("Suggested follow-up"), str(recommendation)))
                for action in parsed.get("proposed_actions", []) or []:
                    if isinstance(action, dict):
                        title = action.get("description") or action.get("action") or action.get("type") or _("Proposed action")
                    else:
                        title = str(action)
                    collected.append((_("Action proposed"), str(title)))
            if not collected:
                ui.label(_("Follow-up ideas will appear after the assistant suggests next steps or proposed actions.")).classes("text-xs opacity-50")
                return
            if note:
                ui.chip(note, icon="my_location").props("outline color=primary")
            for kind, text in collected[:8]:
                with ui.column().classes("w-full gap-1 border rounded-lg p-2"):
                    ui.label(kind).classes("text-[11px] uppercase tracking-wide opacity-50")
                    ui.label(text).classes("text-xs")
                    ui.button(_("Use as follow-up"), icon="reply", on_click=lambda t=text: message_input.set_value(t)).props("flat dense size=sm")

    def update_selector_enabled() -> None:
        saved_thread_selected = bool(render_state.selected_conversation_id)
        group_select.set_enabled(not saved_thread_selected)
        greenhouse_select.set_enabled(bool(scope_state.group_id) and not saved_thread_selected)
        zone_select.set_enabled(bool(scope_state.greenhouse_id) and not saved_thread_selected)
        clear_scope_button.set_enabled(not saved_thread_selected)
        delete_conversation_button.set_enabled(saved_thread_selected)

    async def delete_conversation(conversation_id: str) -> None:
        try:
            async with api_client(timeout=10.0) as client:
                resp = await client.delete(f"/api/ai/conversations/{conversation_id}")
                resp.raise_for_status()
            ui.notify(_("Conversation deleted"), type="warning")
            if render_state.selected_conversation_id == conversation_id:
                start_new_conversation()
            await load_conversations()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                ui.notify(_("Conversation no longer exists"), type="warning")
                if render_state.selected_conversation_id == conversation_id:
                    start_new_conversation()
                await load_conversations()
                return
            detail = response_error(exc.response)
            ui.notify(_("Delete conversation failed: {detail}", detail=detail), type="negative")
            logger.warning("Conversation %s delete failed: %s", conversation_id, exc)
        except httpx.HTTPError as exc:
            ui.notify(_("Delete conversation failed: {detail}", detail=str(exc)), type="negative")
            logger.warning("Conversation %s delete failed: %s", conversation_id, exc)

    def open_delete_dialog() -> None:
        conversation_id = render_state.selected_conversation_id
        if not conversation_id:
            return
        with ui.dialog() as dialog, ui.card().classes("gap-3"):
            ui.label(_("Delete conversation?")).classes("text-lg font-semibold")
            ui.label(_("This will permanently delete this conversation, its messages, and tool-call history.")).classes("text-sm opacity-70")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(_("Cancel"), on_click=dialog.close).props("flat")
                ui.button(
                    _("Delete"),
                    icon="delete",
                    on_click=lambda cid=conversation_id: (dialog.close(), ui.timer(0, lambda: delete_conversation(cid), once=True)),
                ).props("color=negative")
        dialog.open()

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
            conversation_id_to_label.clear()
            options: list[str] = []
            for conv in conversations:
                conv_id = str(conv.get("id", ""))
                title = conv.get("title") or conv_id[:8]
                label = _option_label(title, conv_id)
                conversation_label_to_id[label] = conv_id
                conversation_id_to_label[conv_id] = label
                options.append(label)
            conversation_select.set_options(options)
            if render_state.selected_conversation_id not in conversation_id_to_label:
                render_state.selected_conversation_id = None
                app.storage.user.pop(last_conversation_key, None)
            conversation_select.set_value(conversation_id_to_label.get(render_state.selected_conversation_id or ""))
            update_selector_enabled()
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
        if value == scope_state.group_id:
            return
        scope_state.select_group(value, display)
        apply_scope_values()
        ui.timer(0, _load_greenhouses_for_selected_group, once=True)

    def choose_greenhouse(label: str | None) -> None:
        value, display = label_value("greenhouse", label)
        if value == scope_state.greenhouse_id:
            return
        scope_state.select_greenhouse(value, display)
        apply_scope_values()
        ui.timer(0, _load_zones_for_selected_greenhouse, once=True)

    def choose_zone(label: str | None) -> None:
        value, display = label_value("zone", label)
        if value == scope_state.zone_id:
            return
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
            with chat_area:
                messages = detail.get("messages", [])
                note = _scope_note(scope_state)
                _render_conversation_messages(
                    messages,
                    tool_calls,
                    scope_note=note,
                    on_approve=lambda cid: _approve_command(cid),
                    on_reject=lambda cid: _reject_command(cid),
                )
            render_ideas(messages, _scope_context_note(scope_state))
        except httpx.HTTPError as exc:
            if render_state.load_is_current(token, conversation_id):
                error_container.clear()
                error_container.set_visibility(True)
                with error_container:
                    ui.label(_("Error loading conversation: {error}", error=exc)).classes("text-red-500 text-sm")

    def select_conversation(label: str | None) -> None:
        conversation_id = conversation_label_to_id.get(label or "")
        token = render_state.select_conversation(conversation_id)
        if conversation_id:
            app.storage.user[last_conversation_key] = conversation_id
        else:
            app.storage.user.pop(last_conversation_key, None)
        update_selector_enabled()
        loading_container.clear()
        loading_container.set_visibility(False)
        error_container.clear()
        error_container.set_visibility(False)
        if conversation_id:
            with chat_area:
                ui.spinner("dots", size="2rem")
                ui.label(_("Loading conversation...")).classes("text-sm opacity-50")
            ui.timer(0.1, lambda: load_conversation_messages(conversation_id, token), once=True)
        else:
            render_ideas([])
            with chat_area:
                _render_conversation_messages([], [])

    def start_new_conversation() -> None:
        render_state.start_new()
        app.storage.user.pop(last_conversation_key, None)
        conversation_select.set_value(None)
        chat_area.clear()
        clear_scope()
        render_ideas([])
        update_selector_enabled()
        with chat_area:
            _render_conversation_messages([], [])

    async def refresh_visible_conversation(
        persisted_conversation_id: str,
        token: int,
        original_conversation_id: str | None,
    ) -> None:
        if not render_state.send_is_current(token, original_conversation_id):
            return
        render_state.selected_conversation_id = persisted_conversation_id
        app.storage.user[last_conversation_key] = persisted_conversation_id
        conversation_select.set_value(conversation_id_to_label.get(persisted_conversation_id))
        load_token = render_state.load_token + 1
        render_state.load_token = load_token
        await load_conversation_messages(persisted_conversation_id, load_token)

    async def retry_message(failed_content: str) -> None:
        message_input.set_value(failed_content)
        await send_message()

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
                user_message_bubble(content.strip(), scope_note=_scope_note(scope_state))
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
                    ui.button(_("Retry"), icon="refresh", on_click=lambda c=content.strip(): retry_message(c)).props("flat color=red size=sm")
            logger.error("AI chat request failed: %s", exc)
        finally:
            is_processing["value"] = False
            send_button.enable()

    render_templates()
    render_ideas([])
    await load_conversations()
    await load_scope_options("group", "/api/groups")
    update_selector_enabled()
    render_scope_status()
    selected_label = conversation_id_to_label.get(render_state.selected_conversation_id or "")
    if selected_label:
        select_conversation(selected_label)
    else:
        with chat_area:
            _render_conversation_messages([], [])
