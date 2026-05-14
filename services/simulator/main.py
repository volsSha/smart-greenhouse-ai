"""Multi-greenhouse MQTT simulator entry point.

Simulates edge nodes publishing telemetry for multiple greenhouse groups,
greenhouses, and zones via MQTT. Runs as a standalone process.

Usage::

    python -m services.simulator.main
    python -m services.simulator.main --groups 2 --greenhouses 3 --zones 2
    python -m services.simulator.main --scenario dry_soil
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to path so `app` is importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import get_settings
from app.core.mqtt_topics import telemetry_topic
from app.schemas.telemetry import TelemetryEnvelope, TelemetryReading
from app.services.mqtt_service import MQTTService
from services.simulator.scenarios import (
    ALL_SCENARIOS,
    Scenario,
    ScenarioReading,
)

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 5.0  # seconds between telemetry bursts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smart Greenhouse MQTT Simulator")
    parser.add_argument("--groups", type=int, default=2, help="Number of greenhouse groups")
    parser.add_argument("--greenhouses", type=int, default=2, help="Greenhouses per group")
    parser.add_argument("--zones", type=int, default=2, help="Zones per greenhouse")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Seconds between telemetry bursts")
    parser.add_argument("--scenario", type=str, default="normal", help=f"Scenario name: {[s.__name__ for s in ALL_SCENARIOS]}")
    parser.add_argument("--once", action="store_true", help="Publish one burst and exit")
    return parser.parse_args()


def build_scenario(name: str) -> Scenario:
    """Look up a scenario class by name (case-insensitive)."""
    for scenario_cls in ALL_SCENARIOS:
        if scenario_cls.__name__.lower().replace("_", "") == name.lower().replace("_", ""):
            return scenario_cls()
    raise ValueError(f"Unknown scenario '{name}'. Available: {[s.__name__ for s in ALL_SCENARIOS]}")


def readings_to_envelope(reading: ScenarioReading, group_id: str, greenhouse_id: str, zone_id: str) -> dict:
    """Convert a ScenarioReading into a TelemetryEnvelope dict for JSON serialization."""
    return TelemetryEnvelope(
        message_id=f"sim-{reading.timestamp.timestamp()}-{reading.sensor_id}-{reading.metric}",
        reading=TelemetryReading(
            group_id=group_id,
            greenhouse_id=greenhouse_id,
            zone_id=zone_id,
            sensor_id=reading.sensor_id,
            metric=reading.metric,
            value=reading.value,
            quality=reading.quality if reading.quality in ("ok", "warn", "error") else "ok",
            timestamp=reading.timestamp,
        ),
    ).model_dump(mode="json")


async def publish_burst(
    mqtt: MQTTService,
    scenario: Scenario,
    num_groups: int,
    greenhouses_per_group: int,
    zones_per_greenhouse: int,
) -> int:
    """Publish one telemetry burst for all groups/greenhouses/zones. Returns count of messages."""
    count = 0
    for g in range(1, num_groups + 1):
        group_id = f"group-{g:03d}"
        for gh in range(1, greenhouses_per_group + 1):
            greenhouse_id = f"gh-{g:03d}{gh}"
            for z in range(1, zones_per_greenhouse + 1):
                zone_id = f"zone-{z:02d}"
                topic = telemetry_topic(group_id, greenhouse_id, zone_id)
                readings = scenario.generate_all_metrics(f"sensor-{group_id}")
                for reading in readings:
                    payload = readings_to_envelope(reading, group_id, greenhouse_id, zone_id)
                    await mqtt.publish(topic, json.dumps(payload))
                    count += 1
    return count


async def run_simulator() -> None:
    args = parse_args()
    settings = get_settings()
    scenario = build_scenario(args.scenario)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    logger.info(
        "Starting simulator: %d groups x %d greenhouses x %d zones, "
        "scenario=%s, interval=%.1fs",
        args.groups,
        args.greenhouses,
        args.zones,
        scenario.name,
        args.interval,
    )

    mqtt = MQTTService(settings.mqtt)
    await mqtt.connect()

    try:
        while True:
            count = await publish_burst(
                mqtt, scenario, args.groups, args.greenhouses, args.zones
            )
            logger.info("Published %d readings (scenario: %s)", count, scenario.name)
            if args.once:
                break
            await asyncio.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Simulator stopped by user")
    finally:
        await mqtt.disconnect()


if __name__ == "__main__":
    asyncio.run(run_simulator())
