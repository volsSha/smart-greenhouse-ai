from __future__ import annotations

from app.ui.components.control_panel_state import ScopeOption
from app.ui.components.greenhouse_map import (
    build_greenhouse_map_model,
    build_greenhouse_svg,
    metric_status,
    zone_at_point,
    zone_has_warning,
)


def test_build_greenhouse_map_model_empty() -> None:
    model = build_greenhouse_map_model([])

    assert model.empty is True
    assert model.zones == []
    assert model.columns == 0


def test_build_greenhouse_map_model_neutral_zones() -> None:
    model = build_greenhouse_map_model(
        [
            ScopeOption(id="zone-1", label="Bed 1"),
            ScopeOption(id="zone-2", label="Bed 2"),
            ScopeOption(id="zone-3", label="Bed 3"),
            ScopeOption(id="zone-4", label="Bed 4"),
        ],
        telemetry_by_zone={
            "zone-1": {"temperature": 24},
            "zone-2": {"temperature": 24},
            "zone-3": {"temperature": 24},
            "zone-4": {"temperature": 24},
        },
    )

    assert model.empty is False
    assert model.columns == 2
    assert [zone.label for zone in model.zones] == ["Bed 1", "Bed 2", "Bed 3", "Bed 4"]
    assert all(not zone.selected for zone in model.zones)


def test_build_greenhouse_map_model_marks_selected_and_pending() -> None:
    model = build_greenhouse_map_model(
        [ScopeOption(id="zone-1", label="Bed 1"), ScopeOption(id="zone-2", label="Bed 2")],
        selected_zone_id="zone-2",
        pending_counts={"zone-1": 2},
        telemetry_by_zone={"zone-1": {"temperature": 24}, "zone-2": {"temperature": 24}},
    )

    zone_1, zone_2 = model.zones
    assert zone_1.pending_count == 2
    assert zone_1.selected is False
    assert "2 pending proposals" in zone_1.aria_label
    assert zone_2.selected is True
    assert "selected" in zone_2.aria_label


def test_build_greenhouse_map_model_marks_no_data() -> None:
    model = build_greenhouse_map_model([ScopeOption(id="zone-1", label="Bed 1")])

    assert model.zones[0].no_data is True
    assert "no telemetry" in model.zones[0].aria_label


def test_zone_has_warning_uses_thresholds() -> None:
    assert zone_has_warning({"temperature": 50}) is True
    assert zone_has_warning({"temperature": 24}) is False


def test_metric_status_unknown_metric_is_neutral() -> None:
    assert metric_status("unknown", 999) == "neutral"


def test_zone_at_point_returns_zone_for_svg_coordinates() -> None:
    model = build_greenhouse_map_model([ScopeOption(id="zone-1", label="Bed 1")])
    zone = model.zones[0]

    assert zone_at_point(model, zone.x + 1, zone.y + 1) == zone
    assert zone_at_point(model, zone.x - 1, zone.y - 1) is None


def test_build_greenhouse_svg_contains_svg_zones_and_badges() -> None:
    model = build_greenhouse_map_model(
        [ScopeOption(id="zone-1", label="Bed 1")],
        selected_zone_id="zone-1",
        pending_counts={"zone-1": 3},
    )

    svg = build_greenhouse_svg(model)

    assert "<svg" in svg
    assert "control-greenhouse-svg" in svg
    assert "data-zone-id=\"zone-1\"" in svg
    assert "control-svg-zone selected pending no-data" in svg
    assert "control-svg-pending-text" in svg
    assert ">3</text>" in svg
