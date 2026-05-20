"""Helpers for plant profile soil moisture UI."""

from __future__ import annotations

from typing import Any

DEFAULT_SOIL_MOISTURE_MIN = 40.0
DEFAULT_SOIL_MOISTURE_OPT = 55.0
DEFAULT_SOIL_MOISTURE_MAX = 70.0


def soil_moisture_order_valid(
    minimum: float | None,
    optimum: float | None,
    maximum: float | None,
) -> bool:
    values = [minimum, optimum, maximum]
    if not all(value is not None for value in values):
        return True
    return minimum <= optimum <= maximum


def find_matching_profile(
    profiles: list[dict[str, Any]],
    crop_name: str | None,
    growth_stage: str | None,
) -> dict[str, Any] | None:
    if not crop_name:
        return None
    normalized_crop = crop_name.strip().lower()
    normalized_stage = (growth_stage or "").strip().lower()
    for profile in profiles:
        profile_crop = str(profile.get("crop_name") or "").strip().lower()
        profile_stage = str(profile.get("growth_stage") or "").strip().lower()
        if profile_crop == normalized_crop and profile_stage == normalized_stage:
            return profile
    return None


def default_soil_moisture_payload(
    crop_name: str,
    growth_stage: str | None,
) -> dict[str, Any]:
    return {
        "crop_name": crop_name,
        "growth_stage": growth_stage or None,
        "soil_moisture_min": DEFAULT_SOIL_MOISTURE_MIN,
        "soil_moisture_opt": DEFAULT_SOIL_MOISTURE_OPT,
        "soil_moisture_max": DEFAULT_SOIL_MOISTURE_MAX,
    }


def empty_soil_moisture_fields(profile: dict[str, Any]) -> dict[str, float]:
    defaults = {
        "soil_moisture_min": DEFAULT_SOIL_MOISTURE_MIN,
        "soil_moisture_opt": DEFAULT_SOIL_MOISTURE_OPT,
        "soil_moisture_max": DEFAULT_SOIL_MOISTURE_MAX,
    }
    return {key: value for key, value in defaults.items() if profile.get(key) is None}


def profile_label(profile: dict[str, Any]) -> str:
    crop_name = str(profile.get("crop_name") or "").strip()
    growth_stage = str(profile.get("growth_stage") or "").strip()
    return f"{crop_name} — {growth_stage}" if growth_stage else crop_name
