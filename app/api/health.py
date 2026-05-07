"""Health check endpoints for liveness and readiness probes.

- GET /api/health/live  -- always returns 200 (liveness)
- GET /api/health/ready -- checks DB, InfluxDB, MQTT; returns 200 or 503
"""

from dataclasses import dataclass, field

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/health", tags=["health"])


@dataclass
class ComponentStatus:
    """Status of a single infrastructure component."""

    name: str
    healthy: bool
    detail: str = ""


@dataclass
class HealthResponse:
    """Response body for health check endpoints."""

    status: str
    components: list[ComponentStatus] = field(default_factory=list)


@router.get("/live")
async def liveness() -> HealthResponse:
    """Liveness probe -- always returns 200 if the process is running."""
    return HealthResponse(status="alive")


@router.get("/ready")
async def readiness(request: Request) -> JSONResponse:
    """Readiness probe -- checks all infrastructure dependencies.

    Returns 200 with component statuses if everything is healthy,
    or 503 with details about failing components.
    """
    from sqlalchemy import text

    components: list[ComponentStatus] = []
    all_healthy = True

    # Check PostgreSQL
    try:
        engine = request.app.state.db_engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        components.append(ComponentStatus(name="database", healthy=True))
    except Exception as exc:
        components.append(
            ComponentStatus(name="database", healthy=False, detail=str(exc))
        )
        all_healthy = False

    # Check InfluxDB
    try:
        client = request.app.state.influx_client
        health = client.health()
        if health.status == "pass" or health.status == "ok":
            components.append(ComponentStatus(name="influxdb", healthy=True))
        else:
            components.append(
                ComponentStatus(
                    name="influxdb",
                    healthy=False,
                    detail=f"InfluxDB health: {health.status}",
                )
            )
            all_healthy = False
    except Exception as exc:
        components.append(
            ComponentStatus(name="influxdb", healthy=False, detail=str(exc))
        )
        all_healthy = False

    # Check MQTT
    try:
        from app.dependencies import create_mqtt_client

        settings = request.app.state.settings
        mqtt_client = create_mqtt_client(settings)
        async with mqtt_client:
            pass
        components.append(ComponentStatus(name="mqtt", healthy=True))
    except Exception as exc:
        components.append(
            ComponentStatus(name="mqtt", healthy=False, detail=str(exc))
        )
        all_healthy = False

    body = HealthResponse(
        status="ready" if all_healthy else "degraded",
        components=components,
    )
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": body.status,
            "components": [
                {"name": c.name, "healthy": c.healthy, "detail": c.detail}
                for c in body.components
            ],
        },
    )
