"""Telemetry REST API endpoints.

Provides read-only endpoints for querying persisted telemetry data
from InfluxDB. All endpoints are scoped to a group and follow the
routes defined in docs/ROUTES.md.

Endpoints:
    GET /api/groups/{group_id}/telemetry/latest
    GET /api/groups/{group_id}/telemetry/summary/today
    GET /api/groups/{group_id}/greenhouses/{greenhouse_id}/telemetry/summary/today
    GET /api/groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/telemetry/summary/today
    GET /api/groups/{group_id}/telemetry/range
    GET /api/groups/{group_id}/telemetry/anomalies
    GET /api/groups/{group_id}/compare-greenhouses
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/api/groups", tags=["telemetry"])


def _get_repository(request: Request):
    """Retrieve the TelemetryRepository from app state."""
    return request.app.state.telemetry_repository


# ------------------------------------------------------------------
# Latest readings
# ------------------------------------------------------------------


@router.get("/{group_id}/telemetry/latest")
async def get_latest(
    request: Request,
    group_id: str,
    greenhouse_id: Optional[str] = Query(default=None),
    zone_id: Optional[str] = Query(default=None),
    metric: Optional[str] = Query(default=None),
):
    """Get the latest telemetry readings across the group."""
    repo = _get_repository(request)
    results = repo.get_latest(
        group_id=group_id,
        greenhouse_id=greenhouse_id,
        zone_id=zone_id,
        metric=metric,
    )
    return {"readings": results, "total": len(results)}


# ------------------------------------------------------------------
# Summaries
# ------------------------------------------------------------------


@router.get("/{group_id}/telemetry/summary/today")
async def get_group_summary_today(request: Request, group_id: str):
    """Get today's aggregate summary for the entire group."""
    repo = _get_repository(request)
    results = repo.get_group_summary(group_id=group_id)
    return {"group_id": group_id, "summaries": results}


@router.get("/{group_id}/greenhouses/{greenhouse_id}/telemetry/summary/today")
async def get_greenhouse_summary_today(
    request: Request,
    group_id: str,
    greenhouse_id: str,
):
    """Get today's aggregate summary for a specific greenhouse."""
    repo = _get_repository(request)
    results = repo.get_greenhouse_summary(
        group_id=group_id,
        greenhouse_id=greenhouse_id,
    )
    return {
        "group_id": group_id,
        "greenhouse_id": greenhouse_id,
        "summaries": results,
    }


@router.get(
    "/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/telemetry/summary/today"
)
async def get_zone_summary_today(
    request: Request,
    group_id: str,
    greenhouse_id: str,
    zone_id: str,
):
    """Get today's aggregate summary for a specific zone."""
    repo = _get_repository(request)
    results = repo.get_zone_summary(
        group_id=group_id,
        greenhouse_id=greenhouse_id,
        zone_id=zone_id,
    )
    return {
        "group_id": group_id,
        "greenhouse_id": greenhouse_id,
        "zone_id": zone_id,
        "summaries": results,
    }


# ------------------------------------------------------------------
# Historical range
# ------------------------------------------------------------------


@router.get("/{group_id}/telemetry/range")
async def get_telemetry_range(
    request: Request,
    group_id: str,
    start: datetime = Query(..., description="Start of time range (ISO 8601)"),
    end: datetime = Query(..., description="End of time range (ISO 8601)"),
    greenhouse_id: Optional[str] = Query(default=None),
    zone_id: Optional[str] = Query(default=None),
    metric: Optional[str] = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=10000),
):
    """Get historical telemetry readings within a time range."""
    repo = _get_repository(request)
    results = repo.get_range(
        group_id=group_id,
        start=start,
        end=end,
        greenhouse_id=greenhouse_id,
        zone_id=zone_id,
        metric=metric,
        limit=limit,
    )
    return {
        "group_id": group_id,
        "readings": results,
        "total": len(results),
        "range": {"start": start.isoformat(), "end": end.isoformat()},
    }


# ------------------------------------------------------------------
# Anomalies
# ------------------------------------------------------------------


@router.get("/{group_id}/telemetry/anomalies")
async def get_anomalies(request: Request, group_id: str):
    """Get detected anomalies within the group (last 24h)."""
    repo = _get_repository(request)
    results = repo.get_anomalies(group_id=group_id)
    return {"group_id": group_id, "anomalies": results, "total": len(results)}


# ------------------------------------------------------------------
# Greenhouse comparison
# ------------------------------------------------------------------


@router.get("/{group_id}/compare-greenhouses")
async def compare_greenhouses(request: Request, group_id: str):
    """Compare current conditions across all greenhouses in the group."""
    repo = _get_repository(request)
    results = repo.compare_greenhouses(group_id=group_id)
    return {"group_id": group_id, "comparison": results}
