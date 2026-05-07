"""Async MQTT connection manager built on top of aiomqtt.

``aiomqtt`` does **not** auto-reconnect, so this service wraps the client
in an explicit reconnect loop with configurable delay and max retries.

Usage::

    service = MQTTService(settings.mqtt)
    await service.connect()

    async def on_message(topic, payload):
        ...

    await service.subscribe("greenhouse-groups/+/+/+/telemetry", on_message)

    # ... run until cancelled ...

    await service.disconnect()
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import aiomqtt

from app.config import MQTTSettings

logger = logging.getLogger(__name__)

# Type alias for message callbacks.
MessageCallback = Callable[[str, bytes], Awaitable[None]]


class MQTTService:
    """Async MQTT client with explicit reconnect loop and callback routing.

    Parameters:
        settings: MQTT broker connection settings.
        reconnect_delay: Seconds to wait between reconnection attempts.
        max_retries: Maximum consecutive reconnection attempts (0 = unlimited).
    """

    def __init__(
        self,
        settings: MQTTSettings,
        reconnect_delay: float = 2.0,
        max_retries: int = 0,
    ) -> None:
        self._settings = settings
        self._reconnect_delay = reconnect_delay
        self._max_retries = max_retries
        self._client: aiomqtt.Client | None = None
        self._subscribers: dict[str, list[MessageCallback]] = {}
        self._running = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to the MQTT broker.

        On failure the method retries up to ``max_retries`` times with
        ``reconnect_delay`` seconds between attempts.
        """
        retries = 0
        last_err: Exception | None = None

        while True:
            try:
                self._client = aiomqtt.Client(
                    hostname=self._settings.host,
                    port=self._settings.port,
                    username=self._settings.username or None,
                    password=self._settings.password or None,
                )
                # aiomqtt connects lazily -- force the TCP connection now.
                await self._client.__aenter__()
                self._running = True
                logger.info(
                    "Connected to MQTT broker at %s:%s",
                    self._settings.host,
                    self._settings.port,
                )
                return
            except Exception as exc:
                last_err = exc
                retries += 1
                if self._max_retries > 0 and retries >= self._max_retries:
                    logger.error(
                        "Failed to connect to MQTT after %d retries: %s",
                        retries,
                        exc,
                    )
                    raise
                logger.warning(
                    "MQTT connection failed (attempt %d/%s): %s -- retrying in %.1fs",
                    retries,
                    str(self._max_retries) if self._max_retries > 0 else "unlimited",
                    exc,
                    self._reconnect_delay,
                )
                await asyncio.sleep(self._reconnect_delay)

    async def disconnect(self) -> None:
        """Gracefully disconnect from the MQTT broker."""
        self._running = False
        if self._client is not None:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:
                logger.warning("Error during MQTT disconnect", exc_info=True)
            self._client = None
            logger.info("Disconnected from MQTT broker")

    # ------------------------------------------------------------------
    # Pub / Sub
    # ------------------------------------------------------------------

    async def publish(self, topic: str, payload: bytes | str, qos: int = 0) -> None:
        """Publish a message to *topic*.

        If the client is disconnected, the publish is silently dropped
        (the reconnect loop will restore connectivity).
        """
        if self._client is None or not self._running:
            logger.warning("MQTT publish skipped -- not connected")
            return

        if isinstance(payload, str):
            payload = payload.encode("utf-8")

        try:
            await self._client.publish(topic, payload, qos=qos)
        except Exception:
            logger.exception("Failed to publish to %s", topic)

    async def subscribe(
        self,
        topic: str,
        callback: MessageCallback,
    ) -> None:
        """Register *callback* for messages on *topic*.

        The callback signature is ``async def callback(topic: str, payload: bytes)``.
        Multiple callbacks may be registered for the same topic.

        Note: the caller must also start :meth:`listen` to begin
        receiving messages.
        """
        self._subscribers.setdefault(topic, []).append(callback)
        logger.info("Subscribed callback %s to topic %s", callback.__qualname__, topic)

        # Subscribe on the broker immediately if connected.
        if self._client is not None and self._running:
            try:
                await self._client.subscribe(topic)
            except Exception:
                logger.exception("Failed to subscribe to %s", topic)

    async def listen(self) -> None:
        """Enter the message dispatch loop.

        Blocks until :meth:`disconnect` is called or an unrecoverable
        error occurs. Reconnects automatically on transient failures.
        """
        if self._client is None:
            raise RuntimeError("Not connected -- call connect() first")

        while self._running:
            try:
                async with aiomqtt.Client(
                    hostname=self._settings.host,
                    port=self._settings.port,
                    username=self._settings.username or None,
                    password=self._settings.password or None,
                ) as client:
                    # Re-subscribe on fresh connection.
                    for topic_pattern in self._subscribers:
                        await client.subscribe(topic_pattern)

                    logger.info("MQTT listener ready -- waiting for messages")

                    async for message in client.messages:
                        if not self._running:
                            break
                        await self._dispatch(str(message.topic), message.payload)

            except asyncio.CancelledError:
                logger.info("MQTT listener cancelled")
                break
            except Exception:
                if not self._running:
                    break
                logger.warning(
                    "MQTT connection lost -- reconnecting in %.1fs",
                    self._reconnect_delay,
                    exc_info=True,
                )
                await asyncio.sleep(self._reconnect_delay)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _dispatch(self, topic: str, payload: bytes) -> None:
        """Route an incoming message to all matching callbacks."""
        for pattern, callbacks in self._subscribers.items():
            if self._topic_matches(pattern, topic):
                for cb in callbacks:
                    try:
                        await cb(topic, payload)
                    except Exception:
                        logger.exception(
                            "Callback %s raised an exception on topic %s",
                            cb.__qualname__,
                            topic,
                        )

    @staticmethod
    def _topic_matches(pattern: str, topic: str) -> bool:
        """Simple MQTT topic pattern matcher (supports ``+`` and ``#``)."""
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")

        pi = 0
        ti = 0
        while pi < len(pattern_parts) and ti < len(topic_parts):
            if pattern_parts[pi] == "#":
                return True
            if pattern_parts[pi] == "+" or pattern_parts[pi] == topic_parts[ti]:
                pi += 1
                ti += 1
            else:
                return False

        # Allow trailing "#"
        if pi == len(pattern_parts) - 1 and pattern_parts[pi] == "#":
            return True

        return pi == len(pattern_parts) and ti == len(topic_parts)
