"""Telemetry ingestion pipeline.

Receives raw MQTT messages, parses the topic hierarchy to extract
group/greenhouse/zone identifiers, validates payloads against
:class:`app.schemas.telemetry.TelemetryEnvelope`, and hands off
valid readings to storage (stubbed for now -- U5 adds InfluxDB).

Design goals:

- **Never crash the subscriber**: all errors are logged and the
  offending message is skipped.
- **Idempotency**: recently processed ``message_id`` values are
  tracked so MQTT QoS replays are silently ignored.
"""

from __future__ import annotations

import json
import logging
import re
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from app.core.safety_limits import VALID_METRICS
from app.schemas.telemetry import TelemetryEnvelope, TelemetryReading, TelemetryValidator

logger = logging.getLogger(__name__)

# Regex that matches the canonical telemetry topic:
#   greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/telemetry
_TELEMETRY_TOPIC_RE = re.compile(
    r"^greenhouse-groups/(?P<group_id>[^/]+)"
    r"/greenhouses/(?P<greenhouse_id>[^/]+)"
    r"/zones/(?P<zone_id>[^/]+)"
    r"/telemetry$"
)

# Maximum number of message IDs to track for idempotency.
_IDEMPOTENCY_CACHE_SIZE = 10_000


class TelemetryIngestion:
    """Ingestion pipeline for MQTT telemetry messages.

    Parameters:
        acceptance_window: How far a reading's timestamp may deviate
            from "now" before being rejected.
        influx_client: Optional InfluxDB client for persisting readings.
            When provided, validated readings are written to InfluxDB.
    """

    def __init__(
        self,
        acceptance_window: timedelta = timedelta(minutes=5),
        influx_client=None,
    ) -> None:
        self._validator = TelemetryValidator(window=acceptance_window)
        self._seen_ids: OrderedDict[str, datetime] = OrderedDict()
        self._processed_count = 0
        self._error_count = 0
        self._influx_client = influx_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_message(self, topic: str, payload: bytes) -> None:
        """Parse and validate a single MQTT message.

        Invalid messages are logged and discarded -- the subscriber loop
        is never interrupted.
        """
        try:
            # 1. Extract identifiers from topic.
            topic_info = self._parse_topic(topic)
            if topic_info is None:
                logger.debug("Ignoring non-telemetry topic: %s", topic)
                return

            # 2. Decode payload.
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as exc:
                self._error_count += 1
                logger.warning(
                    "Invalid JSON payload on topic %s: %s", topic, exc
                )
                return

            # 3. Parse envelope + reading.
            try:
                envelope = TelemetryEnvelope.model_validate(data)
            except Exception as exc:
                self._error_count += 1
                logger.warning(
                    "Payload validation failed on topic %s: %s -- payload: %.200s",
                    topic,
                    exc,
                    payload.decode("utf-8", errors="replace"),
                )
                return

            reading = envelope.reading

            # 4. Verify topic identifiers match payload identifiers.
            if (
                reading.group_id != topic_info["group_id"]
                or reading.greenhouse_id != topic_info["greenhouse_id"]
                or reading.zone_id != topic_info["zone_id"]
            ):
                self._error_count += 1
                logger.warning(
                    "Topic/payload ID mismatch on %s: topic says "
                    "%s/%s/%s but payload says %s/%s/%s",
                    topic,
                    topic_info["group_id"],
                    topic_info["greenhouse_id"],
                    topic_info["zone_id"],
                    reading.group_id,
                    reading.greenhouse_id,
                    reading.zone_id,
                )
                return

            # 5. Idempotency check.
            if envelope.message_id is not None:
                if self._is_duplicate(envelope.message_id):
                    logger.debug(
                        "Duplicate message_id=%s -- skipping", envelope.message_id
                    )
                    return
                self._record_id(envelope.message_id)

            # 6. Timestamp freshness check.
            try:
                self._validator.validate_timestamp(reading.timestamp)
            except ValueError as exc:
                self._error_count += 1
                logger.warning("Timestamp validation failed: %s", exc)
                return

            # 7. Hand off to storage (stubbed -- U5 adds InfluxDB).
            await self._store(reading)
            self._processed_count += 1

        except Exception:
            # Absolute safety net -- never propagate exceptions into
            # the MQTT listener loop.
            self._error_count += 1
            logger.exception(
                "Unexpected error processing message on topic %s", topic
            )

    @staticmethod
    def is_valid_metric(metric: str) -> bool:
        """Return ``True`` if *metric* is in the allowed set."""
        return metric in VALID_METRICS

    @property
    def processed_count(self) -> int:
        """Total number of successfully processed messages."""
        return self._processed_count

    @property
    def error_count(self) -> int:
        """Total number of messages that failed validation."""
        return self._error_count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_topic(topic: str) -> dict[str, str] | None:
        """Extract group/greenhouse/zone IDs from a telemetry topic.

        Returns ``None`` if the topic does not match the expected pattern.
        """
        m = _TELEMETRY_TOPIC_RE.match(topic)
        if m is None:
            return None
        return {
            "group_id": m.group("group_id"),
            "greenhouse_id": m.group("greenhouse_id"),
            "zone_id": m.group("zone_id"),
        }

    def _is_duplicate(self, message_id: str) -> bool:
        return message_id in self._seen_ids

    def _record_id(self, message_id: str) -> None:
        """Track a message ID, evicting the oldest entry if the cache is full."""
        self._seen_ids[message_id] = datetime.now(timezone.utc)
        if len(self._seen_ids) > _IDEMPOTENCY_CACHE_SIZE:
            self._seen_ids.popitem(last=False)

    async def _store(self, reading: TelemetryReading) -> None:
        """Persist a validated reading to InfluxDB.

        Uses the InfluxDB client provided at construction time.
        Falls back to a debug log if no client is configured.
        """
        if self._influx_client is not None:
            from app.repositories.telemetry_repository import TelemetryRepository

            repo = TelemetryRepository(self._influx_client)
            repo.write_telemetry(reading)
            logger.debug(
                "Stored reading in InfluxDB: %s/%s/%s sensor=%s metric=%s value=%.2f",
                reading.group_id,
                reading.greenhouse_id,
                reading.zone_id,
                reading.sensor_id,
                reading.metric,
                reading.value,
            )
        else:
            logger.debug(
                "No InfluxDB client configured -- skipping storage: "
                "%s/%s/%s sensor=%s metric=%s value=%.2f",
                reading.group_id,
                reading.greenhouse_id,
                reading.zone_id,
                reading.sensor_id,
                reading.metric,
                reading.value,
            )
