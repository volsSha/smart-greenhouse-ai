"""Unit tests for AI chat view model transformations.

Tests the pure data transformation and formatting functions used by the
AI chat UI components. No UI rendering is involved.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone


from app.ui.pages.ai_chat import (
    ChatRenderState,
    ChatScopeState,
    ScopeOption,
    _build_scope_dict,
    _option_maps,
    _parse_assistant_content,
    _scope_context_note,
    _scope_note,
)
from app.ui.components.tool_call_trace import _truncate_value, _format_duration
from app.ui.components.chat_message import _format_timestamp


# ---------------------------------------------------------------------------
# _parse_assistant_content
# ---------------------------------------------------------------------------


class TestParseAssistantContent:
    """Tests for parsing persisted assistant JSON content."""

    def test_valid_json_structured_response(self) -> None:
        """Parses a full structured AI response JSON string."""
        content = json.dumps({
            "summary": "All greenhouses look healthy.",
            "observations": ["Temperature is 22C in all zones."],
            "recommendations": ["Consider reducing ventilation at night."],
            "proposed_actions": [],
            "status": "ok",
        })
        result = _parse_assistant_content(content)

        assert result["summary"] == "All greenhouses look healthy."
        assert len(result["observations"]) == 1
        assert len(result["recommendations"]) == 1
        assert result["proposed_actions"] == []
        assert result["status"] == "ok"

    def test_invalid_json_falls_back_to_summary(self) -> None:
        """Non-JSON content is treated as a plain summary."""
        content = "This is a plain text response."
        result = _parse_assistant_content(content)

        assert result["summary"] == "This is a plain text response."
        assert result["observations"] == []
        assert result["recommendations"] == []
        assert result["proposed_actions"] == []

    def test_empty_string_falls_back_gracefully(self) -> None:
        """Empty string returns a safe default structure."""
        result = _parse_assistant_content("")

        assert result["summary"] == ""
        assert result["observations"] == []

    def test_partial_json_missing_fields(self) -> None:
        """Partial JSON missing optional fields uses defaults."""
        content = json.dumps({"summary": "Partial data"})
        result = _parse_assistant_content(content)

        assert result["summary"] == "Partial data"
        assert result["observations"] == []
        assert result["recommendations"] == []
        assert result["proposed_actions"] == []

    def test_json_with_proposed_actions(self) -> None:
        """Parses proposed actions from the assistant content."""
        content = json.dumps({
            "summary": "Soil is dry.",
            "proposed_actions": [
                {
                    "actuator": "pump",
                    "action": "on",
                    "duration_seconds": 30,
                    "reason": "Soil moisture below threshold.",
                    "zone_id": "zone-01",
                }
            ],
        })
        result = _parse_assistant_content(content)

        assert len(result["proposed_actions"]) == 1
        assert result["proposed_actions"][0]["actuator"] == "pump"

    def test_ukrainian_missing_threshold_text_is_preserved(self) -> None:
        """Ukrainian missing-threshold wording survives persisted JSON parsing."""
        content = json.dumps({
            "summary": "Відсутні оптимальні пороги вологості ґрунту для цієї зони.",
            "observations": ["Профіль культури не містить soil_moisture_opt."],
            "recommendations": ["Звірте поріг з агротехнічними вимогами культури."],
            "status": "insufficient_data",
        })

        result = _parse_assistant_content(content)

        assert "оптимальні пороги вологості ґрунту" in result["summary"]
        assert result["recommendations"] == ["Звірте поріг з агротехнічними вимогами культури."]
        assert result["status"] == "insufficient_data"

    def test_none_input_falls_back(self) -> None:
        """None input is handled gracefully."""
        result = _parse_assistant_content(None)  # type: ignore[arg-type]

        assert result["summary"] == ""
        assert result["observations"] == []


# ---------------------------------------------------------------------------
# _build_scope_dict
# ---------------------------------------------------------------------------


class TestBuildScopeDict:
    """Tests for building scope dictionaries from UI inputs."""

    def test_all_fields_populated(self) -> None:
        result = _build_scope_dict("group-001", "gh-001", "zone-01")

        assert result == {
            "group_id": "group-001",
            "greenhouse_id": "gh-001",
            "zone_id": "zone-01",
        }

    def test_all_fields_none(self) -> None:
        result = _build_scope_dict(None, None, None)

        assert result == {
            "group_id": None,
            "greenhouse_id": None,
            "zone_id": None,
        }

    def test_partial_scope(self) -> None:
        result = _build_scope_dict("group-001", None, None)

        assert result["group_id"] == "group-001"
        assert result["greenhouse_id"] is None
        assert result["zone_id"] is None

    def test_empty_strings_become_none(self) -> None:
        result = _build_scope_dict("", "", "")

        assert result == {
            "group_id": None,
            "greenhouse_id": None,
            "zone_id": None,
        }


# ---------------------------------------------------------------------------
# ChatScopeState
# ---------------------------------------------------------------------------


class TestChatScopeState:
    """Tests for canonical scope state transformations."""

    def test_selected_scope_builds_api_dict_without_message_tokens(self) -> None:
        state = ChatScopeState()
        state.select_group("11111111-1111-1111-1111-111111111111", "North · 11111111")
        state.select_greenhouse("22222222-2222-2222-2222-222222222222", "GH A · 22222222")
        state.select_zone("33333333-3333-3333-3333-333333333333", "Zone A · 33333333")

        assert state.to_dict() == {
            "group_id": "11111111-1111-1111-1111-111111111111",
            "greenhouse_id": "22222222-2222-2222-2222-222222222222",
            "zone_id": "33333333-3333-3333-3333-333333333333",
        }

    def test_no_scope_is_fleet_wide(self) -> None:
        state = ChatScopeState()

        assert state.to_dict() == {
            "group_id": None,
            "greenhouse_id": None,
            "zone_id": None,
        }
        assert state.can_send()

    def test_changing_group_clears_dependent_scope(self) -> None:
        state = ChatScopeState(
            group_id="group-a",
            greenhouse_id="greenhouse-a",
            zone_id="zone-a",
            labels={"group": "Group A", "greenhouse": "GH A", "zone": "Zone A"},
        )

        state.select_group("group-b", "Group B")

        assert state.group_id == "group-b"
        assert state.greenhouse_id is None
        assert state.zone_id is None
        assert state.labels == {"group": "Group B"}

    def test_removing_greenhouse_clears_zone(self) -> None:
        state = ChatScopeState(group_id="group-a", greenhouse_id="gh-a", zone_id="zone-a")

        state.select_greenhouse(None)

        assert state.group_id == "group-a"
        assert state.greenhouse_id is None
        assert state.zone_id is None

    def test_rehydrate_marks_unresolved_ids(self) -> None:
        state = ChatScopeState()

        state.rehydrate(
            "group-a",
            "greenhouse-a",
            "zone-a",
            {"group": {"group-a": "Group A"}, "greenhouse": {}, "zone": {}},
        )

        assert state.labels["group"] == "Group A"
        assert "greenhouse" in state.unresolved
        assert "zone" in state.unresolved
        assert not state.can_send()

    def test_rehydrate_resolves_dependent_scope_labels_after_options_load(self) -> None:
        state = ChatScopeState()

        state.rehydrate(
            "group-a",
            "greenhouse-a",
            "zone-a",
            {
                "group": {"group-a": "Group A"},
                "greenhouse": {"greenhouse-a": "GH A"},
                "zone": {"zone-a": "Zone A"},
            },
        )

        assert state.labels == {"group": "Group A", "greenhouse": "GH A", "zone": "Zone A"}
        assert state.unresolved == set()
        assert state.can_send()

    def test_clear_resets_all_scope_fields(self) -> None:
        state = ChatScopeState(
            group_id="group-a",
            greenhouse_id="gh-a",
            zone_id="zone-a",
            labels={"group": "Group A"},
            unresolved={"zone"},
        )

        state.clear()

        assert state.to_dict() == {"group_id": None, "greenhouse_id": None, "zone_id": None}
        assert state.labels == {}
        assert state.unresolved == set()


class TestScopeNotes:
    """Tests for scope labels shown in chat and ideas panel."""

    def test_user_scope_note_uses_sent_to_label(self) -> None:
        state = ChatScopeState(group_id="group-a", labels={"group": "Group A · group-a"})

        assert _scope_note(state) == "Sent to: Group: Group A"

    def test_ideas_scope_note_uses_context_label(self) -> None:
        state = ChatScopeState()

        assert _scope_context_note(state) == "Scope: All greenhouses"


class TestScopeOptionMaps:
    """Tests for duplicate-safe label and canonical ID mappings."""

    def test_duplicate_names_keep_distinct_labels_and_ids(self) -> None:
        first = "11111111-1111-1111-1111-111111111111"
        second = "22222222-2222-2222-2222-222222222222"

        label_to_id, id_to_label = _option_maps([
            ScopeOption(first, "North"),
            ScopeOption(second, "North"),
        ])

        assert len(label_to_id) == 2
        assert label_to_id[f"North · {first[:8]}"] == first
        assert label_to_id[f"North · {second[:8]}"] == second
        assert id_to_label[first] != id_to_label[second]


class TestChatRenderState:
    """Tests for async render guards."""

    def test_stale_conversation_load_is_not_current_after_switch(self) -> None:
        state = ChatRenderState()
        token_a = state.select_conversation("conversation-a")
        token_b = state.select_conversation("conversation-b")

        assert not state.load_is_current(token_a, "conversation-a")
        assert state.load_is_current(token_b, "conversation-b")

    def test_send_is_stale_after_conversation_switch(self) -> None:
        state = ChatRenderState(selected_conversation_id="conversation-a")
        token, target = state.start_send()

        state.select_conversation("conversation-b")

        assert not state.send_is_current(token, target)

    def test_start_new_invalidates_load_and_send_tokens(self) -> None:
        state = ChatRenderState(selected_conversation_id="conversation-a")
        load_token = state.load_token
        send_token = state.send_token

        state.start_new()

        assert state.selected_conversation_id is None
        assert state.load_token > load_token
        assert state.send_token > send_token


# ---------------------------------------------------------------------------
# _truncate_value (tool_call_trace)
# ---------------------------------------------------------------------------


class TestTruncateValue:
    """Tests for value truncation in tool call traces."""

    def test_none_returns_null_string(self) -> None:
        assert _truncate_value(None) == "null"

    def test_short_dict_not_truncated(self) -> None:
        value = {"key": "value"}
        result = _truncate_value(value, max_length=200)
        assert '"key": "value"' in result

    def test_long_dict_is_truncated(self) -> None:
        value = {"data": "x" * 300}
        result = _truncate_value(value, max_length=100)
        assert result.endswith("...")
        assert len(result) < 200

    def test_number_value(self) -> None:
        assert _truncate_value(42) == "42"

    def test_string_value(self) -> None:
        assert _truncate_value("hello") == '"hello"'

    def test_list_value(self) -> None:
        assert _truncate_value([1, 2, 3]) == "[1, 2, 3]"


# ---------------------------------------------------------------------------
# _format_duration (tool_call_trace)
# ---------------------------------------------------------------------------


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_none_returns_empty(self) -> None:
        assert _format_duration(None) == ""

    def test_milliseconds(self) -> None:
        assert _format_duration(500) == "500ms"

    def test_seconds(self) -> None:
        assert _format_duration(1500) == "1.5s"

    def test_zero(self) -> None:
        assert _format_duration(0) == "0ms"


# ---------------------------------------------------------------------------
# _format_timestamp (chat_message)
# ---------------------------------------------------------------------------


class TestFormatTimestamp:
    """Tests for timestamp formatting in chat messages."""

    def test_none_returns_empty(self) -> None:
        assert _format_timestamp(None) == ""

    def test_datetime_object(self) -> None:
        dt = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        assert _format_timestamp(dt) == "14:30"

    def test_iso_string(self) -> None:
        assert _format_timestamp("2025-01-15T14:30:00") == "14:30"

    def test_iso_string_with_timezone(self) -> None:
        assert _format_timestamp("2025-01-15T14:30:00Z") == "14:30"

    def test_non_iso_string(self) -> None:
        """Non-parseable strings are returned as-is (truncated)."""
        result = _format_timestamp("some-random-string")
        assert result == "some-random-string"

    def test_long_string_truncated(self) -> None:
        long_str = "a" * 30
        result = _format_timestamp(long_str)
        assert len(result) == 19
