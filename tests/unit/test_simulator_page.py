"""Tests for the simulator page."""

from __future__ import annotations

from app.ui.pages.simulator import SCENARIOS, _scenario_description, _scenario_label


class TestScenarioHelpers:
    def test_all_scenarios_have_labels(self) -> None:
        for key in SCENARIOS:
            label = _scenario_label(key)
            assert label, f"Missing label for {key}"

    def test_all_scenarios_have_descriptions(self) -> None:
        for key in SCENARIOS:
            desc = _scenario_description(key)
            assert desc, f"Missing description for {key}"

    def test_unknown_key_returns_key_itself(self) -> None:
        assert _scenario_label("nonexistent") == "nonexistent"
        assert _scenario_description("nonexistent") == ""

    def test_scenario_config_structure(self) -> None:
        for key, cfg in SCENARIOS.items():
            assert "label" in cfg
            assert "description" in cfg
            assert "icon" in cfg
            assert "color" in cfg
