"""AI chat page with conversation management and tool transparency.

Provides a NiceGUI page where users can ask natural-language questions
about groups, greenhouses, or zones and inspect the tool calls behind
each AI response.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import httpx
from nicegui import ui

from app.i18n.core import _
from app.ui.api_client import api_client, response_error

from app.ui.components.chat_message import (
    assistant_message_bubble,
    system_message,
    user_message_bubble,
)
from app.ui.components.proposed_action_card import proposed_action_card
from app.ui.components.tool_call_trace import tool_call_panel
from app.ui.layouts.main_layout import main_layout

logger = logging.getLogger(__name__)

# In-memory message store for the current page session.
# Messages are refreshed from the API when a conversation is selected.
_SESSION_MESSAGES: list[dict[str, Any]] = []


def _build_scope_dict(
    group_id: str | None,
    greenhouse_id: str | None,
    zone_id: str | None,
) -> dict[str, str | None]:
    """Build a scope dict for the API request."""
    return {
        "group_id": group_id or None,
        "greenhouse_id": greenhouse_id or None,
        "zone_id": zone_id or None,
    }


_DEFAULTS: dict[str, Any] = {
    "observations": [],
    "recommendations": [],
    "proposed_actions": [],
}


def _parse_assistant_content(content: str) -> dict[str, Any]:
    """Parse persisted assistant JSON content into a structured dict.

    Always returns a dict with at least 'summary', 'observations',
    'recommendations', and 'proposed_actions' keys.
    """
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {"summary": str(content) if content else "", **_DEFAULTS}

    if not isinstance(parsed, dict):
        return {"summary": str(content) if content else "", **_DEFAULTS}

    # Fill in defaults for any missing keys
    for key, default in _DEFAULTS.items():
        parsed.setdefault(key, default)
    return parsed


def _render_conversation_messages(
    messages: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    on_approve: Callable[[str], Any] | None = None,
    on_reject: Callable[[str], Any] | None = None,
) -> None:
    """Render all messages from a conversation into the chat area.

    Parameters:
        messages: List of message dicts with 'role', 'content', and optional 'created_at'.
        tool_calls: List of tool call dicts for transparency display.
    """
    if not messages:
        with ui.column().classes("w-full items-center gap-4 mt-20"):
            ui.icon("forum", size="4rem").classes("opacity-30")
            ui.label(_("No messages yet")).classes("text-lg opacity-50")
            ui.label(
                _("Ask a question about your greenhouses, zones, or sensor data.")
            ).classes("text-sm opacity-40")
        return

    # Group tool calls by message order (associate with the last assistant message)
    tool_calls_by_idx: dict[int, list[dict[str, Any]]] = {}
    if tool_calls:
        # Associate all tool calls with the first assistant message
        # (tool calls happen during assistant processing)
        assistant_indices = [
            i for i, m in enumerate(messages) if m.get("role") == "assistant"
        ]
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

                # Tool call transparency for this assistant message
                associated_tools = tool_calls_by_idx.get(idx, [])
                if associated_tools:
                    tool_call_panel(associated_tools)

                # Proposed action cards with approval/rejection
                proposed_actions = parsed.get("proposed_actions", [])
                if proposed_actions:
                    with ui.column().classes("w-full gap-2 mt-2"):
                        ui.label(_("Proposed Actions")).classes("text-xs font-semibold opacity-60")
                        for action in proposed_actions:
                            proposed_action_card(
                                action,
                                on_approve=on_approve,
                                on_reject=on_reject,
                            )
            elif role == "system":
                system_message(content)


@ui.page("/ai-chat")
async def ai_chat() -> None:
    """Render the AI chat page with conversation management."""
    main_layout()

    ui.label(_("AI Assistant")).classes("text-2xl font-bold mt-6")

    # --- State ---
    selected_conversation_id: dict[str, str | None] = {"value": None}
    scope_state: dict[str, str | None] = {
        "group_id": None,
        "greenhouse_id": None,
        "zone_id": None,
    }
    is_processing: dict[str, bool] = {"value": False}

    # --- Top controls row ---
    with ui.row().classes("w-full gap-4 mt-4 items-center flex-wrap"):
        # Conversation selector
        conversation_select = ui.select(
            label=_("Conversation"),
            options={},
            on_change=lambda e: select_conversation(e.value),
        ).classes("flex-1 min-w-[200px]")

        # Scope selectors
        with ui.row().classes("items-center gap-2"):
            ui.label(_("Scope:")).classes("text-sm opacity-60")
            group_input = ui.input(
                label=_("Group ID"),
                placeholder="group-001",
                on_change=lambda e: scope_state.update({"group_id": e.value or None}),
            ).classes("w-32")
            greenhouse_input = ui.input(
                label=_("Greenhouse"),
                placeholder="gh-001",
                on_change=lambda e: scope_state.update({"greenhouse_id": e.value or None}),
            ).classes("w-32")
            zone_input = ui.input(
                label=_("Zone"),
                placeholder="zone-01",
                on_change=lambda e: scope_state.update({"zone_id": e.value or None}),
            ).classes("w-32")

    # --- Chat messages area ---
    chat_area = ui.column().classes("w-full gap-4 mt-4 flex-1 overflow-y-auto")
    chat_area.style("max-height: 60vh; min-height: 300px;")

    # --- Loading / error state containers ---
    loading_container = ui.column().classes("w-full items-center gap-2 mt-4")
    loading_container.set_visibility(False)
    error_container = ui.column().classes("w-full mt-4")
    error_container.set_visibility(False)

    # --- Message input ---
    with ui.row().classes("w-full gap-2 mt-4 items-end sticky bottom-0 bg-white py-2"):
        message_input = ui.textarea(
            placeholder=_("Ask about your greenhouses..."),
        ).classes("flex-1").props('rows=1 autogrow outlined dense')
        send_button = ui.button(
            _("Send"),
            icon="send",
            on_click=lambda: send_message(),
        ).props("color=primary")

    # --- New conversation button ---
    ui.button(
        _("New Conversation"),
        icon="add",
        on_click=lambda: start_new_conversation(),
    ).classes("mt-2").props("flat color=grey")

    # --- Functions ---

    async def load_conversations() -> None:
        """Fetch and populate the conversation selector."""
        try:
            async with api_client(timeout=10.0) as client:
                resp = await client.get("/api/ai/conversations")
                resp.raise_for_status()
                conversations = resp.json()

            options: dict[str, str] = {}
            for conv in conversations:
                conv_id = str(conv.get("id", ""))
                title = conv.get("title") or conv_id[:8]
                options[conv_id] = title

            conversation_select.set_options(options)

        except httpx.HTTPError:
            logger.warning("Failed to load conversations", exc_info=True)

    async def _approve_command(command_id: str) -> None:
        """Approve and execute a proposed command."""
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
        """Reject (cancel) a proposed command."""
        try:
            async with api_client(timeout=15.0) as client:
                resp = await client.post(f"/api/commands/{command_id}/cancel")
                resp.raise_for_status()
            ui.notify(_("Command rejected"), type="warning")
        except httpx.HTTPError as exc:
            detail = response_error(exc.response) if isinstance(exc, httpx.HTTPStatusError) else str(exc)
            ui.notify(_("Rejection failed: {detail}", detail=detail), type="negative")
            logger.warning("Command %s rejection failed: %s", command_id, exc)

    async def load_conversation_messages(conversation_id: str) -> None:
        """Fetch messages and tool calls for a conversation and render them."""
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

            messages = detail.get("messages", [])
            _render_conversation_messages(
                messages, tool_calls,
                on_approve=lambda cid: _approve_command(cid),
                on_reject=lambda cid: _reject_command(cid),
            )

        except httpx.HTTPError as exc:
            ui.label(_("Error loading conversation: {error}", error=exc)).classes("text-red-500 text-sm")

    def select_conversation(conversation_id: str | None) -> None:
        """Handle conversation selection change."""
        selected_conversation_id["value"] = conversation_id
        if conversation_id:
            ui.timer(0.1, lambda: load_conversation_messages(conversation_id), once=True)

    def start_new_conversation() -> None:
        """Clear the current conversation and reset the chat area."""
        selected_conversation_id["value"] = None
        conversation_select.set_value(None)
        chat_area.clear()
        _SESSION_MESSAGES.clear()
        _render_conversation_messages([], [])

    async def send_message() -> None:
        """Send a message to the AI chat endpoint and render the response."""
        if is_processing["value"]:
            return

        content = message_input.value
        if not content or not content.strip():
            return

        is_processing["value"] = True
        send_button.disable()
        message_input.set_value("")

        # Show user message immediately
        with chat_area:
            user_message_bubble(content.strip())

        # Show loading state
        loading_container.clear()
        loading_container.set_visibility(True)
        with loading_container:
            ui.spinner("dots", size="2rem")
            ui.label(_("Thinking...")).classes("text-sm opacity-50")

        # Hide error
        error_container.clear()
        error_container.set_visibility(False)

        try:
            scope = _build_scope_dict(
                scope_state["group_id"],
                scope_state["greenhouse_id"],
                scope_state["zone_id"],
            )

            payload: dict[str, Any] = {
                "message": content.strip(),
                "scope": scope,
            }
            if selected_conversation_id["value"]:
                payload["conversation_id"] = selected_conversation_id["value"]

            async with api_client(timeout=60.0) as client:
                resp = await client.post("/api/ai/chat", json=payload)
                resp.raise_for_status()
                ai_response = resp.json()

            # Hide loading
            loading_container.clear()
            loading_container.set_visibility(False)

            # Parse and render assistant response
            summary = ai_response.get("summary", "")
            observations = ai_response.get("observations", [])
            recommendations = ai_response.get("recommendations", [])
            proposed_actions = ai_response.get("proposed_actions", [])
            status = ai_response.get("status", "ok")

            # Update conversation ID from response if new
            conversation_id = ai_response.get("conversation_id")

            with chat_area:
                assistant_message_bubble(
                    content=summary,
                    observations=observations,
                    recommendations=recommendations,
                    status=status,
                )

                # Proposed action cards with approval/rejection
                if proposed_actions:
                    with ui.column().classes("w-full gap-2 mt-2"):
                        ui.label(_("Proposed Actions")).classes(
                            "text-xs font-semibold opacity-60"
                        )
                        for action in proposed_actions:
                            proposed_action_card(
                                action,
                                on_approve=lambda cid: _approve_command(cid),
                                on_reject=lambda cid: _reject_command(cid),
                            )

            # Refresh conversation list
            await load_conversations()

        except httpx.HTTPError as exc:
            loading_container.clear()
            loading_container.set_visibility(False)

            error_container.clear()
            error_container.set_visibility(True)
            with error_container:
                ui.label(_("Request failed")).classes("text-red-500 font-semibold")
                detail = response_error(exc.response) if isinstance(exc, httpx.HTTPStatusError) else str(exc)
                ui.label(detail).classes("text-sm text-red-400")
                ui.button(
                    _("Retry"),
                    icon="refresh",
                    on_click=lambda: send_message(),
                ).props("flat color=red size=sm")

            logger.error("AI chat request failed: %s", exc)

        finally:
            is_processing["value"] = False
            send_button.enable()

    # --- Initial load ---
    await load_conversations()
    _render_conversation_messages([], [])
