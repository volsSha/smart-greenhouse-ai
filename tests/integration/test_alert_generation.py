"""Integration tests for threshold -> alert generation pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.alert import Alert
from app.models.plant_batch import PlantProfile
from app.services.threshold_service import ThresholdService, ThresholdResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile(**overrides) -> PlantProfile:
    """Create a PlantProfile with defaults that can be overridden."""
    defaults = dict(
        id=uuid.uuid4(),
        crop_name="Tomato",
        growth_stage="fruiting",
        temp_min=18.0,
        temp_opt=24.0,
        temp_max=30.0,
        humidity_min=50.0,
        humidity_opt=65.0,
        humidity_max=80.0,
        soil_moisture_min=40.0,
        soil_moisture_opt=55.0,
        soil_moisture_max=70.0,
        co2_min=300.0,
        co2_opt=600.0,
        co2_max=1000.0,
        light_min=200.0,
        light_opt=500.0,
        light_max=800.0,
        description=None,
    )
    defaults.update(overrides)
    return PlantProfile(**defaults)


def _make_zone(zone_id: uuid.UUID, greenhouse_id: uuid.UUID) -> MagicMock:
    zone = MagicMock()
    zone.id = zone_id
    zone.greenhouse_id = greenhouse_id
    zone.name = "Growing Area A"
    return zone


def _make_greenhouse(
    greenhouse_id: uuid.UUID, group_id: uuid.UUID
) -> MagicMock:
    gh = MagicMock()
    gh.id = greenhouse_id
    gh.group_id = group_id
    return gh


def _make_batch(
    species: str = "Tomato", growth_stage: str = "fruiting"
) -> MagicMock:
    batch = MagicMock()
    batch.id = uuid.uuid4()
    batch.species = species
    batch.growth_stage = growth_stage
    return batch


def _make_alert(**overrides) -> MagicMock:
    defaults = dict(
        id=uuid.uuid4(),
        group_id=uuid.uuid4(),
        greenhouse_id=uuid.uuid4(),
        zone_id=uuid.uuid4(),
        metric="temperature",
        severity="warning",
        title="temperature warning in zone Growing Area A",
        message="32.0 is above maximum threshold (max 30.0)",
        status="active",
        source="threshold",
    )
    defaults.update(overrides)
    alert = MagicMock()
    for k, v in defaults.items():
        setattr(alert, k, v)
    return alert


# ---------------------------------------------------------------------------
# End-to-end threshold evaluation tests
# ---------------------------------------------------------------------------


class TestThresholdAlertGeneration:
    """Test the full pipeline: readings -> threshold check -> alert creation."""

    @pytest.mark.anyio
    async def test_in_range_readings_produce_no_alerts(self) -> None:
        """All readings within range should not create any alerts."""
        zone_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        group_id = uuid.uuid4()

        zone = _make_zone(zone_id, gh_id)
        greenhouse = _make_greenhouse(gh_id, group_id)
        batch = _make_batch()
        profile = _make_profile()

        mock_session = MagicMock()

        with (
            patch(
                "app.services.threshold_service.ZoneRepository",
                autospec=True,
            ) as mock_zone_cls,
            patch(
                "app.services.threshold_service.PlantBatchRepository",
                autospec=True,
            ) as mock_batch_cls,
            patch(
                "app.services.threshold_service.PlantProfileRepository",
                autospec=True,
            ) as mock_profile_cls,
            patch(
                "app.services.threshold_service.GreenhouseRepository",
                autospec=True,
            ) as mock_gh_cls,
            patch(
                "app.services.threshold_service.AlertRepository",
                autospec=True,
            ) as mock_alert_cls,
        ):
            mock_zone_cls.return_value.get_by_id = AsyncMock(
                return_value=zone
            )
            mock_batch_cls.return_value.list_by_zone = AsyncMock(
                return_value=[batch]
            )
            mock_profile_cls.return_value.find_by_crop_and_stage = AsyncMock(
                return_value=profile
            )
            mock_gh_cls.return_value.get_by_id = AsyncMock(
                return_value=greenhouse
            )
            mock_alert_repo = mock_alert_cls.return_value
            mock_alert_repo.create = AsyncMock()

            service = ThresholdService(mock_session)
            alerts = await service.evaluate_zone(
                zone_id,
                {
                    "temperature": 24.0,
                    "air_humidity": 65.0,
                    "soil_moisture": 55.0,
                },
            )

        assert alerts == []
        mock_alert_repo.create.assert_not_called()

    @pytest.mark.anyio
    async def test_out_of_range_readings_produce_alerts(self) -> None:
        """Readings outside range should create alerts."""
        zone_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        group_id = uuid.uuid4()

        zone = _make_zone(zone_id, gh_id)
        greenhouse = _make_greenhouse(gh_id, group_id)
        batch = _make_batch()
        profile = _make_profile()  # temp_max = 30.0
        alert = _make_alert()

        mock_session = MagicMock()

        with (
            patch(
                "app.services.threshold_service.ZoneRepository",
                autospec=True,
            ) as mock_zone_cls,
            patch(
                "app.services.threshold_service.PlantBatchRepository",
                autospec=True,
            ) as mock_batch_cls,
            patch(
                "app.services.threshold_service.PlantProfileRepository",
                autospec=True,
            ) as mock_profile_cls,
            patch(
                "app.services.threshold_service.GreenhouseRepository",
                autospec=True,
            ) as mock_gh_cls,
            patch(
                "app.services.threshold_service.AlertRepository",
                autospec=True,
            ) as mock_alert_cls,
        ):
            mock_zone_cls.return_value.get_by_id = AsyncMock(
                return_value=zone
            )
            mock_batch_cls.return_value.list_by_zone = AsyncMock(
                return_value=[batch]
            )
            mock_profile_cls.return_value.find_by_crop_and_stage = AsyncMock(
                return_value=profile
            )
            mock_gh_cls.return_value.get_by_id = AsyncMock(
                return_value=greenhouse
            )
            mock_alert_repo = mock_alert_cls.return_value
            mock_alert_repo.create = AsyncMock(return_value=alert)

            service = ThresholdService(mock_session)
            alerts = await service.evaluate_zone(
                zone_id,
                {"temperature": 32.0},  # above temp_max of 30.0
            )

        assert len(alerts) == 1
        mock_alert_repo.create.assert_called_once()
        call_kwargs = mock_alert_repo.create.call_args.kwargs
        assert call_kwargs["severity"] == "warning"
        assert call_kwargs["metric"] == "temperature"
        assert call_kwargs["source"] == "threshold"
        assert call_kwargs["status"] == "active"
        assert call_kwargs["group_id"] == group_id
        assert call_kwargs["zone_id"] == zone_id

    @pytest.mark.anyio
    async def test_critical_severity_for_far_out_of_range(self) -> None:
        """Readings far outside range should create critical alerts."""
        zone_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        group_id = uuid.uuid4()

        zone = _make_zone(zone_id, gh_id)
        greenhouse = _make_greenhouse(gh_id, group_id)
        batch = _make_batch()
        profile = _make_profile()  # temp_max=30, range=12, margin=2.4
        alert = _make_alert(severity="critical")

        mock_session = MagicMock()

        with (
            patch(
                "app.services.threshold_service.ZoneRepository",
                autospec=True,
            ) as mock_zone_cls,
            patch(
                "app.services.threshold_service.PlantBatchRepository",
                autospec=True,
            ) as mock_batch_cls,
            patch(
                "app.services.threshold_service.PlantProfileRepository",
                autospec=True,
            ) as mock_profile_cls,
            patch(
                "app.services.threshold_service.GreenhouseRepository",
                autospec=True,
            ) as mock_gh_cls,
            patch(
                "app.services.threshold_service.AlertRepository",
                autospec=True,
            ) as mock_alert_cls,
        ):
            mock_zone_cls.return_value.get_by_id = AsyncMock(
                return_value=zone
            )
            mock_batch_cls.return_value.list_by_zone = AsyncMock(
                return_value=[batch]
            )
            mock_profile_cls.return_value.find_by_crop_and_stage = AsyncMock(
                return_value=profile
            )
            mock_gh_cls.return_value.get_by_id = AsyncMock(
                return_value=greenhouse
            )
            mock_alert_repo = mock_alert_cls.return_value
            mock_alert_repo.create = AsyncMock(return_value=alert)

            service = ThresholdService(mock_session)
            # 35.0 is 5.0 above max(30), margin is 2.4 -> critical
            alerts = await service.evaluate_zone(
                zone_id,
                {"temperature": 35.0},
            )

        assert len(alerts) == 1
        call_kwargs = mock_alert_repo.create.call_args.kwargs
        assert call_kwargs["severity"] == "critical"

    @pytest.mark.anyio
    async def test_multiple_metrics_generate_multiple_alerts(self) -> None:
        """Multiple out-of-range metrics should create multiple alerts."""
        zone_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        group_id = uuid.uuid4()

        zone = _make_zone(zone_id, gh_id)
        greenhouse = _make_greenhouse(gh_id, group_id)
        batch = _make_batch()
        profile = _make_profile()
        alert1 = _make_alert(metric="temperature")
        alert2 = _make_alert(metric="air_humidity")

        mock_session = MagicMock()

        with (
            patch(
                "app.services.threshold_service.ZoneRepository",
                autospec=True,
            ) as mock_zone_cls,
            patch(
                "app.services.threshold_service.PlantBatchRepository",
                autospec=True,
            ) as mock_batch_cls,
            patch(
                "app.services.threshold_service.PlantProfileRepository",
                autospec=True,
            ) as mock_profile_cls,
            patch(
                "app.services.threshold_service.GreenhouseRepository",
                autospec=True,
            ) as mock_gh_cls,
            patch(
                "app.services.threshold_service.AlertRepository",
                autospec=True,
            ) as mock_alert_cls,
        ):
            mock_zone_cls.return_value.get_by_id = AsyncMock(
                return_value=zone
            )
            mock_batch_cls.return_value.list_by_zone = AsyncMock(
                return_value=[batch]
            )
            mock_profile_cls.return_value.find_by_crop_and_stage = AsyncMock(
                return_value=profile
            )
            mock_gh_cls.return_value.get_by_id = AsyncMock(
                return_value=greenhouse
            )
            mock_alert_repo = mock_alert_cls.return_value
            mock_alert_repo.create = AsyncMock(
                side_effect=[alert1, alert2]
            )

            service = ThresholdService(mock_session)
            alerts = await service.evaluate_zone(
                zone_id,
                {
                    "temperature": 32.0,  # above max 30
                    "air_humidity": 85.0,  # above max 80
                    "soil_moisture": 55.0,  # in range
                },
            )

        assert len(alerts) == 2
        assert mock_alert_repo.create.call_count == 2

    @pytest.mark.anyio
    async def test_no_profile_returns_no_alerts(self) -> None:
        """When no matching profile exists, no alerts should be generated."""
        zone_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        group_id = uuid.uuid4()

        zone = _make_zone(zone_id, gh_id)
        greenhouse = _make_greenhouse(gh_id, group_id)
        batch = _make_batch()

        mock_session = MagicMock()

        with (
            patch(
                "app.services.threshold_service.ZoneRepository",
                autospec=True,
            ) as mock_zone_cls,
            patch(
                "app.services.threshold_service.PlantBatchRepository",
                autospec=True,
            ) as mock_batch_cls,
            patch(
                "app.services.threshold_service.PlantProfileRepository",
                autospec=True,
            ) as mock_profile_cls,
            patch(
                "app.services.threshold_service.GreenhouseRepository",
                autospec=True,
            ) as mock_gh_cls,
        ):
            mock_zone_cls.return_value.get_by_id = AsyncMock(
                return_value=zone
            )
            mock_batch_cls.return_value.list_by_zone = AsyncMock(
                return_value=[batch]
            )
            mock_profile_cls.return_value.find_by_crop_and_stage = AsyncMock(
                return_value=None  # No matching profile
            )
            mock_gh_cls.return_value.get_by_id = AsyncMock(
                return_value=greenhouse
            )

            service = ThresholdService(mock_session)
            alerts = await service.evaluate_zone(
                zone_id,
                {"temperature": 100.0},  # way out of range but no profile
            )

        assert alerts == []

    @pytest.mark.anyio
    async def test_alert_message_contains_zone_name(self) -> None:
        """Alert title should include the zone name."""
        zone_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        group_id = uuid.uuid4()

        zone = _make_zone(zone_id, gh_id)
        zone.name = "Nursery Zone"
        greenhouse = _make_greenhouse(gh_id, group_id)
        batch = _make_batch()
        profile = _make_profile()
        alert = _make_alert()

        mock_session = MagicMock()

        with (
            patch(
                "app.services.threshold_service.ZoneRepository",
                autospec=True,
            ) as mock_zone_cls,
            patch(
                "app.services.threshold_service.PlantBatchRepository",
                autospec=True,
            ) as mock_batch_cls,
            patch(
                "app.services.threshold_service.PlantProfileRepository",
                autospec=True,
            ) as mock_profile_cls,
            patch(
                "app.services.threshold_service.GreenhouseRepository",
                autospec=True,
            ) as mock_gh_cls,
            patch(
                "app.services.threshold_service.AlertRepository",
                autospec=True,
            ) as mock_alert_cls,
        ):
            mock_zone_cls.return_value.get_by_id = AsyncMock(
                return_value=zone
            )
            mock_batch_cls.return_value.list_by_zone = AsyncMock(
                return_value=[batch]
            )
            mock_profile_cls.return_value.find_by_crop_and_stage = AsyncMock(
                return_value=profile
            )
            mock_gh_cls.return_value.get_by_id = AsyncMock(
                return_value=greenhouse
            )
            mock_alert_repo = mock_alert_cls.return_value
            mock_alert_repo.create = AsyncMock(return_value=alert)

            service = ThresholdService(mock_session)
            alerts = await service.evaluate_zone(
                zone_id,
                {"temperature": 32.0},
            )

        assert len(alerts) == 1
        call_kwargs = mock_alert_repo.create.call_args.kwargs
        assert "Nursery Zone" in call_kwargs["title"]
