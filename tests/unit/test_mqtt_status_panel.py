"""Tests for MQTT status panel helpers."""

from __future__ import annotations

from pathlib import Path

from app.ui.components.mqtt_status_panel import status_color, status_label


PANEL_SOURCE = (
    Path(__file__).resolve().parents[2] / "app/ui/components/mqtt_status_panel.py"
).read_text(encoding="utf-8")


class TestMQTTStatusPanelHelpers:
    def test_connected_status(self) -> None:
        status = {"connected": True, "reconnecting": False}
        assert status_color(status) == "positive"
        assert status_label(status) == "Connected"

    def test_reconnecting_status(self) -> None:
        status = {"connected": False, "reconnecting": True}
        assert status_color(status) == "warning"
        assert status_label(status) == "Reconnecting"

    def test_disconnected_status(self) -> None:
        status = {"connected": False, "reconnecting": False}
        assert status_color(status) == "negative"
        assert status_label(status) == "Disconnected"

    def test_panel_guidance_mentions_micropython_public_broker_workflow(self) -> None:
        assert "firmware/wokwi-greenhouse-zone/main.py" in PANEL_SOURCE
        assert "firmware/wokwi-greenhouse-zone/config.py" in PANEL_SOURCE
        assert "public MQTT broker" in PANEL_SOURCE
        assert "MicroPython" in PANEL_SOURCE

    def test_panel_guidance_no_longer_uses_private_gateway_or_cpp_wording(self) -> None:
        assert "Private Gateway" not in PANEL_SOURCE
        assert "host.wokwi.internal" not in PANEL_SOURCE
        assert "main.cpp" not in PANEL_SOURCE
        assert "PlatformIO" not in PANEL_SOURCE
