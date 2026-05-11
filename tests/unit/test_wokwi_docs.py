"""Tests for Wokwi MQTT/ngrok developer documentation."""

from __future__ import annotations

from pathlib import Path

DOC = Path("docs/wokwi-mqtt-mode.md")
FIRMWARE_README = Path("firmware/wokwi-greenhouse-zone/README.md")


def _combined_docs() -> str:
    return DOC.read_text() + "\n" + FIRMWARE_README.read_text()


class TestWokwiMqttModeDocs:
    """Keep the hosted Wokwi local-broker setup documented."""

    def test_docs_explain_ngrok_tcp_to_local_mosquitto(self) -> None:
        docs = _combined_docs().lower()
        for required in (
            "hosted wokwi",
            "ngrok tcp",
            "11883",
            "docker mosquitto",
            "localhost:11883",
        ):
            assert required in docs

    def test_docs_point_to_config_py_for_ngrok_host_and_port(self) -> None:
        docs = _combined_docs()
        for required in (
            "firmware/wokwi-greenhouse-zone/config.py",
            "config.py",
            "MQTT_HOST",
            "MQTT_PORT",
            "ngrok",
        ):
            assert required in docs

    def test_docs_warn_about_free_tier_stale_ngrok_endpoint(self) -> None:
        docs = _combined_docs().lower()
        assert "free-tier" in docs or "free tier" in docs
        assert "stale" in docs
        assert "host" in docs
        assert "port" in docs
        assert "change" in docs or "not stable" in docs

    def test_docs_include_verification_checklist(self) -> None:
        docs = _combined_docs().lower()
        assert "verification checklist" in docs
        for required in (
            "mosquitto",
            "ngrok",
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
            "stale ngrok host",
            "wrong target zone",
            "11883",
            "config.py",
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
