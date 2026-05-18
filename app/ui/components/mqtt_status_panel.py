"""NiceGUI MQTT/Wokwi status panel component."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from app.i18n.core import _


def status_color(status: dict[str, Any]) -> str:
    if status.get("connected"):
        return "positive"
    if status.get("reconnecting"):
        return "warning"
    return "negative"


def status_label(status: dict[str, Any]) -> str:
    if status.get("connected"):
        return _("Connected")
    if status.get("reconnecting"):
        return _("Reconnecting")
    return _("Disconnected")


class MQTTStatusPanel:
    """Small status card for Wokwi/MQTT mode."""

    def __init__(self) -> None:
        self._badge = None
        self._broker = None
        self._last_message = None
        self._last_topic = None
        self._counts = None
        self._error = None

    def render(self) -> None:
        with ui.card().classes("w-full"):
            with ui.row().classes("items-center justify-between w-full"):
                ui.label(_("Wokwi / MQTT Status")).classes("text-lg font-bold")
                self._badge = ui.badge(_("Unknown"), color="grey")

            self._broker = ui.label("").classes("text-sm font-mono mt-2")
            self._last_message = ui.label("").classes("text-sm opacity-70")
            self._last_topic = ui.label("").classes("text-xs font-mono opacity-50")
            self._counts = ui.label("").classes("text-xs opacity-60")
            self._error = ui.label("").classes("text-xs text-red-500")

            ui.separator().classes("my-2")
            ui.label(_("Firmware path: firmware/wokwi-greenhouse-zone/main.py")).classes(
                "text-xs font-mono opacity-70"
            )
            ui.label(
                _(
                    "Use a public MQTT broker, then paste its host, port, and credentials into "
                    "firmware/wokwi-greenhouse-zone/config.py for the hosted Wokwi MicroPython simulator."
                )
            ).classes("text-xs opacity-60")

    def update(self, status: dict[str, Any]) -> None:
        if self._badge is None:
            return

        self._badge.set_text(status_label(status))
        self._badge._props["color"] = status_color(status)
        self._badge.update()

        broker = f"Broker: {status.get('broker_host', '')}:{status.get('broker_port', '')}"
        topic = status.get("subscribed_topic") or "not subscribed"
        self._broker.set_text(f"{broker} | Subscribed: {topic}")

        last_message = status.get("last_message_at") or "waiting for telemetry"
        self._last_message.set_text(f"Last telemetry: {last_message}")
        self._last_topic.set_text(f"Last topic: {status.get('last_topic') or '--'}")
        self._counts.set_text(
            f"Processed: {status.get('processed_count', 0)} | Errors: {status.get('error_count', 0)}"
        )
        self._error.set_text(status.get("last_error") or "")
