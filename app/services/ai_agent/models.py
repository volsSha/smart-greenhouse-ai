"""Schemas for structured AI agent responses and tool logs."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIScope(BaseModel):
    """Scope for an AI conversation or response."""

    group_id: str | None = None
    greenhouse_id: str | None = None
    zone_id: str | None = None


class AIResponseStatus(StrEnum):
    """Allowed status values for structured AI responses."""

    OK = "ok"
    INSUFFICIENT_DATA = "insufficient_data"


class AIResponse(BaseModel):
    """Structured response returned by the greenhouse AI agent."""

    model_config = ConfigDict(extra="forbid")

    scope: AIScope
    status: AIResponseStatus

    @field_validator("scope", mode="before")
    @classmethod
    def coerce_global_scope(cls, scope: Any) -> Any:
        if isinstance(scope, str):
            return {}
        return scope
    summary: str = Field(min_length=1)
    observations: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    proposed_actions: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("proposed_actions")
    @classmethod
    def proposed_actions_require_confirmation(
        cls,
        actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Ensure physical-action proposals are marked for approval flow."""
        for action in actions:
            action.setdefault("requires_confirmation", True)
        return actions


class ToolCallLog(BaseModel):
    """Sanitized record of a tool invocation."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_summary: dict[str, Any] | str | None = None
    status: str
    error: str | None = None
    duration_ms: int | None = None
