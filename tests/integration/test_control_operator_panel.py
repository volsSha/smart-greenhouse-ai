from __future__ import annotations

from pathlib import Path


def test_control_page_source_removes_raw_uuid_form() -> None:
    source = Path("app/ui/pages/control.py").read_text()

    assert "Greenhouse Overview" in source
    map_source = Path("app/ui/components/greenhouse_map.py").read_text()

    assert "build_greenhouse_map_model" in source
    assert "render_zone_control_drawer" in source
    assert "enable_demo_mode" in source
    assert "Demo Greenhouse" in source
    assert "Demo command proposed" in source
    assert "Control mode" in source
    assert "Offline demo fallback" in source
    assert "MQTT remote control" in source
    assert "Simulator control" in source
    assert "Simulator is not running" in source
    assert "ui.interactive_image" in map_source
    assert "<svg" in map_source
    assert "control-greenhouse-svg" in map_source
    assert "Group ID" not in source
    assert "Zone ID" not in source
    assert "_SAMPLE_GROUP_ID" not in source
    assert "_SAMPLE_ZONE_ID" not in source


def test_control_page_refresh_preserves_selected_zone_source() -> None:
    source = Path("app/ui/pages/control.py").read_text()

    assert "previous_zone_id = selected_zone.id if selected_zone else None" in source
    assert "selected_zone = selected_or_first(zones, previous_zone_id)" in source
    assert "await refresh_commands()" in source
