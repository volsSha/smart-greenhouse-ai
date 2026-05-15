"""Pure state helpers for the control operator panel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.command_service import CommandStatus

PENDING_COMMAND_STATUSES = {
    CommandStatus.PROPOSED,
    CommandStatus.VALIDATED,
    CommandStatus.APPROVED,
    "proposed",
    "validated",
    "approved",
}


@dataclass(frozen=True)
class ScopeOption:
    id: str
    label: str


@dataclass(frozen=True)
class PlantContext:
    primary: dict[str, Any] | None = None
    additional_count: int = 0


@dataclass(frozen=True)
class ZoneContext:
    group: ScopeOption
    greenhouse: ScopeOption
    zone: ScopeOption
    telemetry: dict[str, Any] = field(default_factory=dict)
    telemetry_unavailable: bool = False
    plant: PlantContext = field(default_factory=PlantContext)
    pending_commands: list[dict[str, Any]] = field(default_factory=list)


def build_scope_options(items: list[dict[str, Any]], *, fallback_prefix: str) -> list[ScopeOption]:
    counts: dict[str, int] = {}
    for item in items:
        label = str(item.get("name") or item.get("label") or item.get("id") or "")
        counts[label] = counts.get(label, 0) + 1

    options: list[ScopeOption] = []
    for index, item in enumerate(items, start=1):
        item_id = str(item.get("id") or item.get("group_id") or item.get("greenhouse_id") or item.get("zone_id") or "")
        base_label = str(item.get("name") or item.get("label") or item_id or f"{fallback_prefix} {index}")
        label = f"{base_label} ({item_id[:8]})" if counts.get(base_label, 0) > 1 and item_id else base_label
        options.append(ScopeOption(id=item_id, label=label))
    return options


def pending_counts_by_zone(commands: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for command in commands:
        if command.get("status") not in PENDING_COMMAND_STATUSES:
            continue
        zone_id = command.get("zone_id")
        if zone_id is None:
            continue
        zone_key = str(zone_id)
        counts[zone_key] = counts.get(zone_key, 0) + 1
    return counts


def pending_commands_for_zone(commands: list[dict[str, Any]], zone_id: str) -> list[dict[str, Any]]:
    return [
        command
        for command in commands
        if str(command.get("zone_id")) == zone_id and command.get("status") in PENDING_COMMAND_STATUSES
    ]


def plant_context_by_zone(plant_batches: list[dict[str, Any]]) -> dict[str, PlantContext]:
    batches_by_zone: dict[str, list[dict[str, Any]]] = {}
    for batch in plant_batches:
        zone_id = batch.get("zone_id")
        if zone_id is None:
            continue
        batches_by_zone.setdefault(str(zone_id), []).append(batch)

    contexts: dict[str, PlantContext] = {}
    for zone_id, batches in batches_by_zone.items():
        ordered = sorted(batches, key=lambda batch: str(batch.get("planted_at") or batch.get("created_at") or ""), reverse=True)
        contexts[zone_id] = PlantContext(primary=ordered[0], additional_count=max(len(ordered) - 1, 0))
    return contexts


def telemetry_by_zone(readings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    telemetry: dict[str, dict[str, Any]] = {}
    for reading in readings:
        zone_id = reading.get("zone_id")
        metric = reading.get("metric")
        if zone_id is None or metric is None:
            continue
        value = reading.get("_value", reading.get("value"))
        telemetry.setdefault(str(zone_id), {})[str(metric)] = value
    return telemetry


def build_zone_context(
    *,
    group: ScopeOption,
    greenhouse: ScopeOption,
    zone: ScopeOption,
    telemetry: dict[str, dict[str, Any]],
    plant_contexts: dict[str, PlantContext],
    commands: list[dict[str, Any]],
    telemetry_failed: bool = False,
) -> ZoneContext:
    zone_telemetry = telemetry.get(zone.id, {})
    return ZoneContext(
        group=group,
        greenhouse=greenhouse,
        zone=zone,
        telemetry=zone_telemetry,
        telemetry_unavailable=telemetry_failed or not zone_telemetry,
        plant=plant_contexts.get(zone.id, PlantContext()),
        pending_commands=pending_commands_for_zone(commands, zone.id),
    )
