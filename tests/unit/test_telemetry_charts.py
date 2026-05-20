from __future__ import annotations

from app.ui.components.telemetry_charts import _build_line_option, _parse_readings, _series_label, chart_size_class


def test_parse_readings_builds_time_value_pairs() -> None:
    points = _parse_readings([
        {"_time": "2026-05-20T10:01:00Z", "_value": 11},
        {"_time": "2026-05-20T10:00:00Z", "_value": 10},
    ])

    assert points == [
        ["2026-05-20T10:00:00Z", 10.0],
        ["2026-05-20T10:01:00Z", 11.0],
    ]


def test_line_option_uses_time_axis_and_zoom() -> None:
    option = _build_line_option(
        "Temperature",
        [{"name": "Temperature", "data": [["2026-05-20T10:00:00Z", 22.0]]}],
        "C",
    )

    assert option["xAxis"]["type"] == "time"
    assert [zoom["type"] for zoom in option["dataZoom"]] == ["inside", "slider"]
    assert option["series"][0]["data"] == [["2026-05-20T10:00:00Z", 22.0]]


def test_series_label_includes_zone_to_avoid_collapsed_metrics() -> None:
    assert _series_label({"zone_id": "zone-01"}, "temperature") == "Temperature / zone-01"


def test_chart_size_class_defaults_to_normal() -> None:
    assert chart_size_class("compact") == "w-full h-56"
    assert chart_size_class("normal") == "w-full h-80"
