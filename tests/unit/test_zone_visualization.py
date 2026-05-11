"""Tests for the zone visualization component."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.ui.components.zone_visualization import (
    METRIC_UNITS,
    ZoneVisualization,
    _metric_status,
)


class TestMetricStatus:
    def test_green_in_range(self) -> None:
        assert _metric_status("temperature", 24.0) == "green"
        assert _metric_status("air_humidity", 60.0) == "green"
        assert _metric_status("soil_moisture", 55.0) == "green"
        assert _metric_status("co2", 850.0) == "green"
        assert _metric_status("light", 500.0) == "green"

    def test_yellow_out_of_green(self) -> None:
        assert _metric_status("temperature", 15.0) == "yellow"
        assert _metric_status("temperature", 30.0) == "yellow"
        assert _metric_status("light", 100.0) == "yellow"

    def test_red_out_of_bounds(self) -> None:
        assert _metric_status("temperature", 50.0) == "red"
        assert _metric_status("temperature", 5.0) == "red"
        assert _metric_status("co2", 2000.0) == "red"

    def test_unknown_metric_returns_green(self) -> None:
        assert _metric_status("unknown", 999.0) == "green"

    def test_boundary_values(self) -> None:
        assert _metric_status("temperature", 18.0) == "green"
        assert _metric_status("temperature", 28.0) == "green"
        assert _metric_status("temperature", 14.0) == "yellow"
        assert _metric_status("temperature", 34.0) == "yellow"


class TestMetrUnits:
    def test_all_five_metrics_present(self) -> None:
        expected = {"temperature", "air_humidity", "soil_moisture", "co2", "light"}
        assert set(METRIC_UNITS) == expected

    def test_each_has_label_and_unit(self) -> None:
        for key, (label, unit) in METRIC_UNITS.items():
            assert isinstance(label, str)
            assert isinstance(unit, str)
            assert len(label) > 0


class TestZoneVisualization:
    """Tests ZoneVisualization container logic."""

    def test_build_and_update_all(self) -> None:
        viz = ZoneVisualization()
        container = MagicMock()
        viz.build(container)
        assert viz._container is container

    def test_update_all_creates_cards(self) -> None:
        viz = ZoneVisualization()
        container = MagicMock()
        viz.build(container)

        zones = [
            {
                "zone_id": "zone-01",
                "temperature": 24.0,
                "air_humidity": 60.0,
                "soil_moisture": 55.0,
                "co2": 850.0,
                "light": 500.0,
                "actuators": {"pump": {"active": False}, "fan": {"active": False},
                              "heater": {"active": False}, "lamp": {"active": False}},
            },
        ]
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.ui.components.zone_visualization._ZoneCard", MagicMock)
            viz.update_all(zones)
            assert "zone-01" in viz._zone_cards

    def test_mark_stopped_greys_all_cards(self) -> None:
        viz = ZoneVisualization()
        mock_card = MagicMock()
        viz._zone_cards["zone-01"] = mock_card

        viz.mark_stopped()
        mock_card.set_stopped.assert_called_once_with(True)

    def test_clear_removes_all_cards(self) -> None:
        viz = ZoneVisualization()
        mock_card = MagicMock()
        viz._zone_cards["zone-01"] = mock_card

        viz.clear()
        mock_card._card.delete.assert_called_once()
        assert len(viz._zone_cards) == 0

    def test_update_all_removes_stale_cards(self) -> None:
        viz = ZoneVisualization()
        container = MagicMock()
        viz.build(container)

        old_card = MagicMock()
        old_card._card = MagicMock()
        viz._zone_cards["zone-old"] = old_card

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.ui.components.zone_visualization._ZoneCard", MagicMock)
            viz.update_all([])
            assert len(viz._zone_cards) == 0
            old_card._card.delete.assert_called_once()
