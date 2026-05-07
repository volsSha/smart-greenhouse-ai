"""Standalone baseline control engine entry point."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import get_settings
from app.dependencies import create_db_engine
from app.services.command_service import CommandService
from services.control_engine.rules import ZoneTelemetrySnapshot, evaluate_zone_rules
from sqlalchemy.ext.asyncio import async_sessionmaker

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smart Greenhouse baseline control engine")
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--greenhouse-id", required=True)
    parser.add_argument("--zone-id", required=True)
    parser.add_argument("--soil-moisture", type=float)
    parser.add_argument("--soil-min", type=float, default=30.0)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--temperature-max", type=float, default=30.0)
    return parser.parse_args()


async def run_control_engine_once() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    readings = {}
    if args.soil_moisture is not None:
        readings["soil_moisture"] = args.soil_moisture
    if args.temperature is not None:
        readings["temperature"] = args.temperature
    snapshot = ZoneTelemetrySnapshot(
        group_id=UUID(args.group_id),
        greenhouse_id=UUID(args.greenhouse_id),
        zone_id=UUID(args.zone_id),
        readings=readings,
        thresholds={
            "soil_moisture": (args.soil_min, None),
            "temperature": (None, args.temperature_max),
        },
    )
    settings = get_settings()
    engine = create_db_engine(settings)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        service = CommandService(session)
        for proposal in evaluate_zone_rules(snapshot):
            command = await service.propose(proposal.command, current_readings=snapshot.readings)
            logger.info("Created %s proposal %s", proposal.severity, command.id)
        await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_control_engine_once())
