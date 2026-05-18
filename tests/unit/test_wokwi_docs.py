"""Tests for Wokwi MQTT developer documentation."""

from __future__ import annotations

from pathlib import Path

DOC = Path("docs/wokwi-mqtt-mode.md")
FIRMWARE_README = Path("firmware/wokwi-greenhouse-zone/README.md")
DEPLOY_GUIDE = Path("docs/deploy-mosquitto-vps.md")


def _combined_docs() -> str:
    return DOC.read_text() + "\n" + FIRMWARE_README.read_text() + "\n" + DEPLOY_GUIDE.read_text()


class TestWokwiMqttModeDocs:
    """Keep the hosted Wokwi public-broker setup documented."""

    def test_docs_explain_public_broker_path(self) -> None:
        docs = _combined_docs().lower()
        for required in (
            "hosted wokwi",
            "public mqtt broker",
            "mosquitto broker on vps",
            "mqtt.example.com",
            "8883",
        ):
            assert required in docs

    def test_docs_point_to_config_py_for_broker_settings(self) -> None:
        docs = _combined_docs()
        for required in (
            "firmware/wokwi-greenhouse-zone/config.py",
            "config.py",
            "MQTT_HOST",
            "MQTT_PORT",
            "MQTT_USER",
            "MQTT_PASSWORD",
        ):
            assert required in docs

    def test_docs_do_not_reference_tunnels(self) -> None:
        docs = _combined_docs().lower()
        assert "ng" + "rok" not in docs

    def test_docs_include_verification_checklist(self) -> None:
        docs = _combined_docs().lower()
        assert "verification checklist" in docs
        for required in (
            "mosquitto",
            "wokwi serial",
            "mqtt connected",
            "status panel",
            "telemetry",
            "command",
        ):
            assert required in docs

    def test_docs_include_required_troubleshooting_paths(self) -> None:
        docs = _combined_docs().lower()
        for required in (
            "connection refused",
            "wrong target zone",
            "config.py",
            "credentials",
            "firewall",
        ):
            assert required in docs

    def test_firmware_readme_documents_project_files_and_hosted_wokwi(self) -> None:
        readme = FIRMWARE_README.read_text().lower()
        for required in (
            "main.py",
            "config.py",
            "diagram.json",
            "hosted wokwi",
            "micropython",
        ):
            assert required in readme
