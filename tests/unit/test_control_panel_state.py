from __future__ import annotations

from app.ui.components.control_panel_state import (
    PlantContext,
    ScopeOption,
    build_scope_options,
    build_zone_context,
    pending_commands_for_zone,
    pending_counts_by_zone,
    plant_context_by_zone,
    telemetry_by_zone,
)


def test_build_scope_options_disambiguates_duplicate_labels() -> None:
    options = build_scope_options(
        [
            {"id": "11111111-0000-0000-0000-000000000001", "name": "North"},
            {"id": "22222222-0000-0000-0000-000000000002", "name": "North"},
        ],
        fallback_prefix="Zone",
    )

    assert options == [
        ScopeOption(id="11111111-0000-0000-0000-000000000001", label="North (11111111)"),
        ScopeOption(id="22222222-0000-0000-0000-000000000002", label="North (22222222)"),
    ]


def test_pending_counts_include_only_active_statuses() -> None:
    counts = pending_counts_by_zone(
        [
            {"zone_id": "zone-1", "status": "proposed"},
            {"zone_id": "zone-1", "status": "validated"},
            {"zone_id": "zone-2", "status": "approved"},
            {"zone_id": "zone-2", "status": "executed"},
            {"zone_id": "zone-3", "status": "cancelled"},
        ]
    )

    assert counts == {"zone-1": 2, "zone-2": 1}


def test_pending_commands_for_zone_filters_zone_and_status() -> None:
    commands = [
        {"id": "1", "zone_id": "zone-1", "status": "proposed"},
        {"id": "2", "zone_id": "zone-2", "status": "proposed"},
        {"id": "3", "zone_id": "zone-1", "status": "executed"},
    ]

    assert pending_commands_for_zone(commands, "zone-1") == [commands[0]]


def test_plant_context_by_zone_uses_newest_primary_and_counts_additional() -> None:
    contexts = plant_context_by_zone(
        [
            {"id": "old", "zone_id": "zone-1", "planted_at": "2026-01-01"},
            {"id": "new", "zone_id": "zone-1", "planted_at": "2026-02-01"},
            {"id": "other", "zone_id": "zone-2", "planted_at": "2026-01-15"},
        ]
    )

    assert contexts["zone-1"] == PlantContext(primary={"id": "new", "zone_id": "zone-1", "planted_at": "2026-02-01"}, additional_count=1)
    assert contexts["zone-2"].additional_count == 0


def test_telemetry_by_zone_groups_metrics() -> None:
    telemetry = telemetry_by_zone(
        [
            {"zone_id": "zone-1", "metric": "temperature", "_value": 22.5},
            {"zone_id": "zone-1", "metric": "soil_moisture", "value": 45},
            {"zone_id": "zone-2", "metric": "temperature", "_value": 24},
        ]
    )

    assert telemetry == {
        "zone-1": {"temperature": 22.5, "soil_moisture": 45},
        "zone-2": {"temperature": 24},
    }


def test_telemetry_by_zone_uses_latest_response_readings() -> None:
    response = {
        "readings": [
            {"zone_id": "zone-1", "metric": "temperature", "_value": 22.5},
        ],
        "total": 1,
    }

    assert telemetry_by_zone(response["readings"]) == {"zone-1": {"temperature": 22.5}}


def test_build_zone_context_keeps_zone_selectable_without_optional_data() -> None:
    context = build_zone_context(
        group=ScopeOption(id="group-1", label="Main Group"),
        greenhouse=ScopeOption(id="gh-1", label="North House"),
        zone=ScopeOption(id="zone-1", label="Bed 1"),
        telemetry={},
        plant_contexts={},
        commands=[{"id": "cmd-1", "zone_id": "zone-1", "status": "proposed"}],
    )

    assert context.zone.label == "Bed 1"
    assert context.telemetry_unavailable is True
    assert context.plant == PlantContext()
    assert context.pending_commands == [{"id": "cmd-1", "zone_id": "zone-1", "status": "proposed"}]
