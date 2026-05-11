"""Tests for Mosquitto ACL topic alignment."""

from __future__ import annotations

from pathlib import Path

from app.core.mqtt_topics import command_topic, state_topic, telemetry_topic

ACL_PATH = Path("infra/mosquitto/acl.conf")
CONFIG_PATH = Path("infra/mosquitto/mosquitto.conf")


def _acl_text() -> str:
    return ACL_PATH.read_text()


def _config_text() -> str:
    return CONFIG_PATH.read_text()


class TestMosquittoAcl:
    def test_mosquitto_config_loads_acl_file(self) -> None:
        text = _config_text()
        assert "acl_file /mosquitto/config/acl.conf" in text

    def test_acl_uses_canonical_topic_root(self) -> None:
        text = _acl_text()
        assert "greenhouse-groups/#" in text
        assert "greenhouse/+" not in text

    def test_wokwi_can_read_commands_and_write_telemetry_state(self) -> None:
        text = _acl_text()
        assert "user wokwi" in text
        assert "topic read greenhouse-groups/+/greenhouses/+/zones/+/commands" in text
        assert "topic write greenhouse-groups/+/greenhouses/+/zones/+/telemetry" in text
        assert "topic write greenhouse-groups/+/greenhouses/+/zones/+/state" in text

    def test_backend_has_readwrite_canonical_access(self) -> None:
        text = _acl_text()
        assert "user app" in text
        assert "topic readwrite greenhouse-groups/#" in text

    def test_acl_patterns_match_topic_builders_shape(self) -> None:
        command = command_topic("group-001", "gh-001", "zone-01")
        telemetry = telemetry_topic("group-001", "gh-001", "zone-01")
        state = state_topic("group-001", "gh-001", "zone-01")

        assert len(command.split("/")) == 7
        assert len(telemetry.split("/")) == 7
        assert len(state.split("/")) == 7
