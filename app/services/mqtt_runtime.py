"""Application-owned MQTT telemetry subscriber runtime."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import MQTTSettings
from app.core.mqtt_topics import all_telemetry_topic
from app.services.mqtt_service import MQTTService
from app.services.telemetry_ingestion import TelemetryIngestion

logger = logging.getLogger(__name__)


@dataclass
class MQTTRuntimeStatus:
    running: bool = False
    connected: bool = False
    reconnecting: bool = False
    subscribed_topic: str | None = None
    broker_host: str = ""
    broker_port: int = 0
    last_message_at: str | None = None
    last_topic: str | None = None
    last_error: str | None = None
    processed_count: int = 0
    error_count: int = 0


class MQTTRuntime:
    """Owns the long-running MQTT telemetry listener task."""

    def __init__(
        self,
        settings: MQTTSettings,
        ingestion: TelemetryIngestion,
        mqtt_service: MQTTService | None = None,
    ) -> None:
        self._settings = settings
        self._ingestion = ingestion
        self._mqtt = mqtt_service or MQTTService(settings)
        self._task: asyncio.Task | None = None
        self._status = MQTTRuntimeStatus(
            broker_host=settings.host,
            broker_port=settings.port,
        )

    async def start(self) -> None:
        """Start the background listener if it is not already running."""
        if self._task and not self._task.done():
            return
        self._status.running = True
        self._status.reconnecting = True
        self._status.last_error = None
        self._task = asyncio.create_task(self._run(), name="mqtt-telemetry-runtime")

    async def stop(self) -> None:
        """Stop the background listener and disconnect MQTT cleanly."""
        self._status.running = False
        self._status.connected = False
        self._status.reconnecting = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        await self._mqtt.disconnect()

    def status(self) -> MQTTRuntimeStatus:
        """Return current runtime status."""
        self._status.processed_count = self._ingestion.processed_count
        self._status.error_count = self._ingestion.error_count
        return self._status

    async def _run(self) -> None:
        topic = all_telemetry_topic()
        self._status.subscribed_topic = topic
        try:
            await self._mqtt.connect()
            await self._mqtt.subscribe(topic, self._handle_message)
            self._status.connected = True
            self._status.reconnecting = False
            await self._mqtt.listen()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._status.connected = False
            self._status.reconnecting = True
            self._status.last_error = str(exc)
            logger.warning("MQTT runtime stopped after listener error", exc_info=True)
        finally:
            self._status.connected = False

    async def _handle_message(self, topic: str, payload: bytes) -> None:
        self._status.last_message_at = datetime.now(timezone.utc).isoformat()
        self._status.last_topic = topic
        await self._ingestion.process_message(topic, payload)
