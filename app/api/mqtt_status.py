"""MQTT runtime status endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/mqtt", tags=["mqtt"])


class MQTTStatusResponse(BaseModel):
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


@router.get("/status", response_model=MQTTStatusResponse)
async def mqtt_status(request: Request) -> MQTTStatusResponse:
    runtime = getattr(request.app.state, "mqtt_runtime", None)
    if runtime is None:
        return MQTTStatusResponse(last_error="MQTT runtime is not initialized")
    return MQTTStatusResponse.model_validate(runtime.status(), from_attributes=True)
