"""Tests for plant profile UI helpers."""

from app.ui.components.plant_profile_helpers import (
    default_soil_moisture_payload,
    empty_soil_moisture_fields,
    find_matching_profile,
    profile_label,
    soil_moisture_order_valid,
)


def test_soil_moisture_order_valid_accepts_empty_values() -> None:
    assert soil_moisture_order_valid(40.0, None, 70.0)


def test_soil_moisture_order_valid_rejects_out_of_order_values() -> None:
    assert not soil_moisture_order_valid(70.0, 55.0, 40.0)


def test_find_matching_profile_matches_crop_and_stage_case_insensitively() -> None:
    profiles = [{"crop_name": "Tomato", "growth_stage": "Seedling", "id": "profile-1"}]

    match = find_matching_profile(profiles, "tomato", "seedling")

    assert match == profiles[0]


def test_default_soil_moisture_payload_contains_editable_starter_values() -> None:
    payload = default_soil_moisture_payload("Tomato", "seedling")

    assert payload == {
        "crop_name": "Tomato",
        "growth_stage": "seedling",
        "soil_moisture_min": 40.0,
        "soil_moisture_opt": 55.0,
        "soil_moisture_max": 70.0,
    }


def test_empty_soil_moisture_fields_fills_only_missing_values() -> None:
    payload = empty_soil_moisture_fields({
        "soil_moisture_min": 41.0,
        "soil_moisture_opt": None,
        "soil_moisture_max": None,
    })

    assert payload == {"soil_moisture_opt": 55.0, "soil_moisture_max": 70.0}


def test_profile_label_includes_growth_stage_when_present() -> None:
    assert profile_label({"crop_name": "Tomato", "growth_stage": "seedling"}) == "Tomato — seedling"


def test_profile_label_uses_crop_name_without_growth_stage() -> None:
    assert profile_label({"crop_name": "Tomato", "growth_stage": None}) == "Tomato"
