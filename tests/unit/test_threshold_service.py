"""Unit tests for the ThresholdService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.plant_batch import PlantProfile
from app.services.threshold_service import ThresholdService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile(
    *,
    temp_min: float = 18.0,
    temp_max: float = 30.0,
    humidity_min: float = 50.0,
    humidity_max: float = 80.0,
    soil_moisture_min: float = 40.0,
    soil_moisture_max: float = 70.0,
    co2_min: float = 300.0,
    co2_max: float = 1000.0,
    light_min: float = 200.0,
    light_max: float = 800.0,
) -> PlantProfile:
    """Create a PlantProfile instance for testing."""
    return PlantProfile(
        id=uuid.uuid4(),
        crop_name="Tomato",
        growth_stage="fruiting",
        temp_min=temp_min,
        temp_opt=24.0,
        temp_max=temp_max,
        humidity_min=humidity_min,
        humidity_opt=65.0,
        humidity_max=humidity_max,
        soil_moisture_min=soil_moisture_min,
        soil_moisture_opt=55.0,
        soil_moisture_max=soil_moisture_max,
        co2_min=co2_min,
        co2_opt=600.0,
        co2_max=co2_max,
        light_min=light_min,
        light_opt=500.0,
        light_max=light_max,
    )


# ---------------------------------------------------------------------------
# Tests for evaluate_readings
# ---------------------------------------------------------------------------


class TestEvaluateReadings:
    """Tests for ThresholdService.evaluate_readings."""

    def test_all_values_in_range_returns_empty(self) -> None:
        """No alerts when all readings are within thresholds."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()

        readings = {
            "temperature": 24.0,
            "air_humidity": 65.0,
            "soil_moisture": 55.0,
            "co2": 600.0,
            "light": 500.0,
        }

        results = service.evaluate_readings(profile, readings)
        assert results == []

    def test_temperature_above_max_generates_warning(self) -> None:
        """Slightly above max generates a warning."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()  # temp_max = 30.0

        readings = {"temperature": 31.5}
        results = service.evaluate_readings(profile, readings)

        assert len(results) == 1
        assert results[0].metric == "temperature"
        assert results[0].severity == "warning"
        assert "31.5" in results[0].message
        assert "30" in results[0].message

    def test_temperature_far_above_max_generates_critical(self) -> None:
        """Far above max generates a critical alert."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()  # temp_max = 30.0, range = 12.0, margin = 2.4

        readings = {"temperature": 34.0}  # 4.0 above max, margin is 2.4
        results = service.evaluate_readings(profile, readings)

        assert len(results) == 1
        assert results[0].metric == "temperature"
        assert results[0].severity == "critical"

    def test_temperature_below_min_generates_warning(self) -> None:
        """Slightly below min generates a warning."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()  # temp_min = 18.0

        readings = {"temperature": 16.5}
        results = service.evaluate_readings(profile, readings)

        assert len(results) == 1
        assert results[0].severity == "warning"

    def test_temperature_far_below_min_generates_critical(self) -> None:
        """Far below min generates a critical alert."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()  # temp_min = 18.0, range = 12.0, margin = 2.4

        readings = {"temperature": 14.0}  # 4.0 below min, margin is 2.4
        results = service.evaluate_readings(profile, readings)

        assert len(results) == 1
        assert results[0].severity == "critical"

    def test_multiple_metrics_out_of_range(self) -> None:
        """Multiple out-of-range readings produce multiple results."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()

        readings = {
            "temperature": 35.0,  # critical
            "air_humidity": 45.0,  # below min 50
            "soil_moisture": 55.0,  # in range
        }
        results = service.evaluate_readings(profile, readings)

        assert len(results) == 2
        metrics = {r.metric for r in results}
        assert metrics == {"temperature", "air_humidity"}

    def test_unknown_metric_is_skipped(self) -> None:
        """Metrics not in the threshold map are silently skipped."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()

        readings = {"unknown_metric": 999.0}
        results = service.evaluate_readings(profile, readings)
        assert results == []

    def test_none_thresholds_are_skipped(self) -> None:
        """Metrics with None min/max on the profile are skipped."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile(temp_min=None, temp_max=None)

        readings = {"temperature": 100.0}
        results = service.evaluate_readings(profile, readings)
        assert results == []

    def test_humidity_above_max(self) -> None:
        """Humidity above max generates warning."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()  # humidity_max = 80.0

        readings = {"air_humidity": 85.0}
        results = service.evaluate_readings(profile, readings)

        assert len(results) == 1
        assert results[0].metric == "air_humidity"
        assert results[0].severity == "warning"

    def test_soil_moisture_below_min(self) -> None:
        """Soil moisture below min generates warning."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()  # soil_moisture_min = 40.0

        readings = {"soil_moisture": 35.0}
        results = service.evaluate_readings(profile, readings)

        assert len(results) == 1
        assert results[0].metric == "soil_moisture"
        assert results[0].severity == "warning"

    def test_soil_moisture_optimal_missing_does_not_skip_min_max_alert(self) -> None:
        """Missing optimal value does not affect min/max threshold alerts."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()
        profile.soil_moisture_opt = None

        results = service.evaluate_readings(profile, {"soil_moisture": 35.0})

        assert len(results) == 1
        assert results[0].metric == "soil_moisture"
        assert results[0].severity == "warning"

    def test_soil_moisture_missing_min_skips_threshold_alert(self) -> None:
        """Missing min or max still skips soil moisture threshold evaluation."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile(soil_moisture_min=None)

        results = service.evaluate_readings(profile, {"soil_moisture": 35.0})

        assert results == []

    def test_co2_out_of_range(self) -> None:
        """CO2 out of range generates alert."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()  # co2_max = 1000.0

        readings = {"co2": 1100.0}
        results = service.evaluate_readings(profile, readings)

        assert len(results) == 1
        assert results[0].metric == "co2"

    def test_light_out_of_range(self) -> None:
        """Light out of range generates alert."""
        session = MagicMock(spec=object)
        service = ThresholdService(session)  # type: ignore[arg-type]
        profile = _make_profile()  # light_min = 200.0

        readings = {"light": 150.0}
        results = service.evaluate_readings(profile, readings)

        assert len(results) == 1
        assert results[0].metric == "light"


# ---------------------------------------------------------------------------
# Tests for evaluate_zone (requires full session mock)
# ---------------------------------------------------------------------------


class TestEvaluateZone:
    """Tests for ThresholdService.evaluate_zone with mocked session."""

    @pytest.mark.anyio
    async def test_missing_zone_returns_empty(self) -> None:
        """Returns empty list when zone is not found."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        service = ThresholdService(mock_session)
        alerts = await service.evaluate_zone(
            uuid.uuid4(),
            {"temperature": 40.0},
        )
        assert alerts == []

    @pytest.mark.anyio
    async def test_zone_without_batches_returns_empty(self) -> None:
        """Returns empty list when zone has no plant batches."""
        zone_id = uuid.uuid4()
        zone = MagicMock()
        zone.greenhouse_id = uuid.uuid4()

        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=zone)

        # Mock the session.execute chain for the list() method
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ThresholdService(mock_session)
        alerts = await service.evaluate_zone(zone_id, {"temperature": 40.0})
        assert alerts == []

    @pytest.mark.anyio
    async def test_missing_profile_returns_empty(self) -> None:
        """Returns empty list when no matching profile is found."""
        zone_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        zone = MagicMock()
        zone.id = zone_id
        zone.greenhouse_id = gh_id
        zone.name = "test-zone"

        batch = MagicMock()
        batch.species = "UnknownCrop"
        batch.growth_stage = None

        greenhouse = MagicMock()
        greenhouse.group_id = uuid.uuid4()
        greenhouse.id = gh_id

        # Build a mock session that behaves like AsyncSession.get and
        # supports the repository pattern internally.
        mock_session = MagicMock()
        mock_session.get = AsyncMock(side_effect=lambda model, pk: None)

        # We need to mock the repositories more carefully.
        # The service creates repos internally, so we patch them.
        from unittest.mock import patch

        with (
            patch(
                "app.services.threshold_service.ZoneRepository",
                autospec=True,
            ) as mock_zone_repo_cls,
            patch(
                "app.services.threshold_service.PlantBatchRepository",
                autospec=True,
            ) as mock_batch_repo_cls,
            patch(
                "app.services.threshold_service.PlantProfileRepository",
                autospec=True,
            ) as mock_profile_repo_cls,
            patch(
                "app.services.threshold_service.GreenhouseRepository",
                autospec=True,
            ) as mock_gh_repo_cls,
        ):
            mock_zone_repo = mock_zone_repo_cls.return_value
            mock_zone_repo.get_by_id = AsyncMock(return_value=zone)

            mock_batch_repo = mock_batch_repo_cls.return_value
            mock_batch_repo.list_by_zone = AsyncMock(return_value=[batch])

            mock_profile_repo = mock_profile_repo_cls.return_value
            mock_profile_repo.find_by_crop_and_stage = AsyncMock(return_value=None)

            mock_gh_repo = mock_gh_repo_cls.return_value
            mock_gh_repo.get_by_id = AsyncMock(return_value=greenhouse)

            service = ThresholdService(mock_session)
            alerts = await service.evaluate_zone(
                zone_id, {"temperature": 40.0}
            )

        assert alerts == []
