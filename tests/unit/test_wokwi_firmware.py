"""Tests for the Wokwi MicroPython firmware project.

These tests keep the Wokwi example MicroPython-first and aligned with the
application MQTT contracts in app/core/mqtt_topics.py, app/schemas/telemetry.py,
and app/services/command_publisher.py.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT = Path("firmware/wokwi-greenhouse-zone")

REQUIRED_METRICS = {"temperature", "air_humidity", "soil_moisture", "co2", "light"}
TELEMETRY_TOPIC_TEMPLATE = (
    "greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/telemetry"
)
COMMAND_TOPIC_TEMPLATE = (
    "greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/commands"
)
COMMAND_PAYLOAD_FIELDS = {
    "command_id",
    "group_id",
    "greenhouse_id",
    "zone_id",
    "actuator",
    "action",
    "value",
    "duration_seconds",
    "source",
    "reason",
}
TELEMETRY_ENVELOPE_FIELDS = {"message_id", "qos", "reading"}
TELEMETRY_READING_FIELDS = {
    "group_id",
    "greenhouse_id",
    "zone_id",
    "sensor_id",
    "metric",
    "value",
    "quality",
    "timestamp",
}


class TestWokwiFirmwareProject:
    """Assert the Wokwi firmware project is MicroPython-first."""

    def test_required_micropython_files_exist(self) -> None:
        assert (PROJECT / "main.py").exists(), "main.py is the authoritative firmware entry point"
        assert (PROJECT / "config.py").exists(), "config.py must hold editable Wokwi MQTT settings"
        assert (PROJECT / "diagram.json").exists(), "diagram.json must define the Wokwi hardware layout"

    def test_cpp_and_platformio_are_not_authoritative(self) -> None:
        assert not (PROJECT / "platformio.ini").exists(), (
            "platformio.ini must be removed or demoted so PlatformIO is not the default path"
        )
        assert not (PROJECT / "src" / "main.cpp").exists(), (
            "src/main.cpp must not remain the authoritative firmware source; use main.py"
        )

    def test_diagram_uses_micropython_main_file(self) -> None:
        data = json.loads((PROJECT / "diagram.json").read_text())
        assert data.get("version") == 1
        assert "main.py" in json.dumps(data), "Wokwi diagram must point users at MicroPython main.py"
        assert "platformio" not in json.dumps(data).lower()
        assert "main.cpp" not in json.dumps(data).lower()

    def test_diagram_has_esp32_sensors_and_actuator_outputs(self) -> None:
        data = json.loads((PROJECT / "diagram.json").read_text())
        part_ids = {part["id"] for part in data["parts"]}
        required = {
            "esp",
            "dht",
            "soil",
            "light",
            "co2",
            "pumpLed",
            "fanLed",
            "heaterLed",
            "lampLed",
        }
        assert required <= part_ids, f"Missing Wokwi parts: {required - part_ids}"

    def test_config_exposes_broker_identity_topics_and_interval(self) -> None:
        code = (PROJECT / "config.py").read_text()
        for name in (
            "MQTT_HOST",
            "MQTT_PORT",
            "MQTT_USER",
            "MQTT_PASSWORD",
            "GROUP_ID",
            "GREENHOUSE_ID",
            "ZONE_ID",
            "DEVICE_ID",
            "PUBLISH_INTERVAL_SECONDS",
            "TELEMETRY_TOPIC_TEMPLATE",
            "COMMAND_TOPIC_TEMPLATE",
        ):
            assert name in code, f"config.py must define {name}"
        assert TELEMETRY_TOPIC_TEMPLATE in code
        assert COMMAND_TOPIC_TEMPLATE in code

    def test_main_imports_config_instead_of_hardcoding_broker(self) -> None:
        code = (PROJECT / "main.py").read_text()
        assert "import config" in code or "from config import" in code
        assert "broker.hivemq.com" not in code
        assert "test.mosquitto.org" not in code

    def test_main_uses_canonical_mqtt_topic_templates(self) -> None:
        code = (PROJECT / "main.py").read_text()
        config_code = (PROJECT / "config.py").read_text()
        combined = code + config_code
        assert TELEMETRY_TOPIC_TEMPLATE in combined
        assert COMMAND_TOPIC_TEMPLATE in combined
        assert "/greenhouses/" in combined
        assert "/zones/" in combined
        assert "/telemetry" in combined
        assert "/commands" in combined

    def test_main_publishes_required_telemetry_metrics(self) -> None:
        code = (PROJECT / "main.py").read_text()
        for metric in REQUIRED_METRICS:
            assert metric in code, f"main.py must publish metric '{metric}'"

    def test_main_publishes_telemetry_envelope_schema(self) -> None:
        code = (PROJECT / "main.py").read_text()
        for field in TELEMETRY_ENVELOPE_FIELDS | TELEMETRY_READING_FIELDS:
            assert field in code, f"main.py telemetry envelope must include '{field}'"

    def test_main_does_not_publish_stale_fallback_timestamp(self) -> None:
        code = (PROJECT / "main.py").read_text()
        assert "2026-01-01T00:00" not in code
        assert "Clock is not synchronized" in code

    def test_main_handles_command_publisher_payload_fields(self) -> None:
        code = (PROJECT / "main.py").read_text()
        for field in COMMAND_PAYLOAD_FIELDS:
            assert field in code, f"main.py must tolerate command payload field '{field}'"

    def test_main_subscribes_to_commands(self) -> None:
        code = (PROJECT / "main.py").read_text().lower()
        assert "set_callback" in code
        assert "subscribe" in code
        assert "command_topic" in code

    def test_main_handles_malformed_commands_without_crashing(self) -> None:
        code = (PROJECT / "main.py").read_text()
        assert "try" in code and "except" in code
        assert "json.loads" in code
        assert "malformed" in code.lower() or "invalid" in code.lower()
        assert "return" in code, "malformed command handling should return to the main loop"
