"""Integration tests for the plants API endpoints."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_group(
    group_id: uuid.UUID | None = None,
    name: str = "Test Group",
) -> MagicMock:
    """Create a mock GreenhouseGroup ORM object."""
    group = MagicMock()
    group.id = group_id or uuid.uuid4()
    group.name = name
    group.location = "Test Location"
    group.description = "Test Description"
    group.created_at = datetime.now(timezone.utc)
    return group


def _make_mock_greenhouse(
    greenhouse_id: uuid.UUID | None = None,
    group_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock Greenhouse ORM object."""
    gh = MagicMock()
    gh.id = greenhouse_id or uuid.uuid4()
    gh.group_id = group_id or uuid.uuid4()
    gh.name = "Test Greenhouse"
    gh.location = "Test Location"
    gh.description = "Test Description"
    gh.created_at = datetime.now(timezone.utc)
    return gh


def _make_mock_zone(
    zone_id: uuid.UUID | None = None,
    greenhouse_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock GreenhouseZone ORM object."""
    zone = MagicMock()
    zone.id = zone_id or uuid.uuid4()
    zone.greenhouse_id = greenhouse_id or uuid.uuid4()
    zone.name = "Test Zone"
    zone.description = "Test Description"
    zone.created_at = datetime.now(timezone.utc)
    return zone


def _make_mock_plant_batch(
    batch_id: uuid.UUID | None = None,
    zone_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock PlantBatch ORM object."""
    batch = MagicMock()
    batch.id = batch_id or uuid.uuid4()
    batch.zone_id = zone_id or uuid.uuid4()
    batch.profile_id = None
    batch.name = "Test Batch"
    batch.species = "Tomato"
    batch.cultivar = "Roma"
    batch.planted_at = None
    batch.growth_stage = "seedling"
    batch.notes = None
    batch.created_at = datetime.now(timezone.utc)
    return batch


def _make_mock_plant_profile(
    profile_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock PlantProfile ORM object."""
    profile = MagicMock()
    profile.id = profile_id or uuid.uuid4()
    profile.crop_name = "Tomato"
    profile.growth_stage = "fruiting"
    profile.temp_min = 18.0
    profile.temp_opt = 24.0
    profile.temp_max = 30.0
    profile.humidity_min = 50.0
    profile.humidity_opt = 65.0
    profile.humidity_max = 80.0
    profile.soil_moisture_min = 40.0
    profile.soil_moisture_opt = 55.0
    profile.soil_moisture_max = 70.0
    profile.co2_min = 300.0
    profile.co2_opt = 600.0
    profile.co2_max = 1000.0
    profile.light_min = 200.0
    profile.light_opt = 500.0
    profile.light_max = 800.0
    profile.description = "Test profile"
    return profile


def _make_mock_session() -> AsyncMock:
    """Create a mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock(return_value=None)
    return session


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create a test client without starting the full lifespan."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Plant Profile API tests
# ---------------------------------------------------------------------------


class TestPlantProfileAPI:
    """Tests for GET/POST /api/plant-profiles."""

    @pytest.mark.anyio
    async def test_list_profiles_empty(self, client: AsyncClient) -> None:
        """GET /api/plant-profiles returns empty list when no profiles exist."""
        mock_session = _make_mock_session()

        # Mock the select().execute() chain for the list() method
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            response = await client.get("/api/plant-profiles")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.anyio
    async def test_create_profile_success(self, client: AsyncClient) -> None:
        """POST /api/plant-profiles creates a new profile."""
        mock_session = _make_mock_session()
        profile = _make_mock_plant_profile()

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            # We need to mock PlantProfileRepository.create
            # Since the endpoint creates a real repo with the session,
            # we make session.flush return the profile via the add side effect
            def capture_add(obj):
                pass

            mock_session.add = MagicMock(side_effect=capture_add)
            mock_session.flush = AsyncMock()

            # Actually, the simplest approach: mock the list() call chain
            # and test create via mocking the session behavior.
            # The repository calls self.session.add(obj) then self.session.flush().
            # We need to ensure the created object has the right attributes.

            # Replace with a more direct approach: patch the repository class
            from unittest.mock import patch

            with patch(
                "app.api.plants.PlantProfileRepository"
            ) as MockRepoClass:
                mock_repo = MockRepoClass.return_value
                mock_repo.create = AsyncMock(return_value=profile)

                payload = {
                    "crop_name": "Tomato",
                    "growth_stage": "fruiting",
                    "temp_min": 18.0,
                    "temp_opt": 24.0,
                    "temp_max": 30.0,
                }
                response = await client.post(
                    "/api/plant-profiles", json=payload
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["crop_name"] == "Tomato"
        assert data["growth_stage"] == "fruiting"
        assert data["temp_min"] == 18.0
        mock_session.commit.assert_awaited_once()

    @pytest.mark.anyio
    async def test_get_profile_success(self, client: AsyncClient) -> None:
        """GET /api/plant-profiles/{id} returns a profile."""
        profile_id = uuid.uuid4()
        mock_session = _make_mock_session()
        profile = _make_mock_plant_profile(profile_id=profile_id)

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch("app.api.plants.PlantProfileRepository") as MockRepoClass:
                MockRepoClass.return_value.get_by_id = AsyncMock(return_value=profile)
                response = await client.get(f"/api/plant-profiles/{profile_id}")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["id"] == str(profile_id)

    @pytest.mark.anyio
    async def test_patch_profile_updates_only_requested_fields(self, client: AsyncClient) -> None:
        """PATCH updates one profile field without requiring the full profile."""
        profile_id = uuid.uuid4()
        mock_session = _make_mock_session()
        profile = _make_mock_plant_profile(profile_id=profile_id)
        profile.soil_moisture_opt = 58.0

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch("app.api.plants.PlantProfileRepository") as MockRepoClass:
                mock_repo = MockRepoClass.return_value
                mock_repo.update = AsyncMock(return_value=profile)
                response = await client.patch(
                    f"/api/plant-profiles/{profile_id}",
                    json={"soil_moisture_opt": 58.0},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["soil_moisture_min"] == 40.0
        assert data["soil_moisture_opt"] == 58.0
        assert data["soil_moisture_max"] == 70.0
        mock_repo.update.assert_awaited_once_with(profile_id, soil_moisture_opt=58.0)
        mock_session.commit.assert_awaited_once()

    @pytest.mark.anyio
    async def test_patch_profile_accepts_null_soil_value(self, client: AsyncClient) -> None:
        """PATCH can clear a nullable soil moisture value."""
        profile_id = uuid.uuid4()
        mock_session = _make_mock_session()
        profile = _make_mock_plant_profile(profile_id=profile_id)
        profile.soil_moisture_opt = None

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch("app.api.plants.PlantProfileRepository") as MockRepoClass:
                MockRepoClass.return_value.update = AsyncMock(return_value=profile)
                response = await client.patch(
                    f"/api/plant-profiles/{profile_id}",
                    json={"soil_moisture_opt": None},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["soil_moisture_opt"] is None

    @pytest.mark.anyio
    async def test_get_profile_not_found(self, client: AsyncClient) -> None:
        """GET returns 404 when a plant profile does not exist."""
        profile_id = uuid.uuid4()
        mock_session = _make_mock_session()

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch("app.api.plants.PlantProfileRepository") as MockRepoClass:
                MockRepoClass.return_value.get_by_id = AsyncMock(return_value=None)
                response = await client.get(f"/api/plant-profiles/{profile_id}")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_patch_profile_rejects_invalid_soil_order(self, client: AsyncClient) -> None:
        """PATCH rejects impossible min/opt/max soil moisture ordering."""
        mock_session = _make_mock_session()

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            response = await client.patch(
                f"/api/plant-profiles/{uuid.uuid4()}",
                json={
                    "soil_moisture_min": 70.0,
                    "soil_moisture_opt": 55.0,
                    "soil_moisture_max": 40.0,
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Plant Batch API tests
# ---------------------------------------------------------------------------


class TestPlantBatchAPI:
    """Tests for plant batch CRUD endpoints."""

    @pytest.mark.anyio
    async def test_list_batches_empty(self, client: AsyncClient) -> None:
        """GET /api/groups/{group_id}/plant-batches returns empty list."""
        group_id = uuid.uuid4()
        mock_session = _make_mock_session()

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch(
                "app.api.plants.GreenhouseRepository"
            ) as MockGhRepo, patch(
                "app.api.plants.ZoneRepository"
            ) as MockZoneRepo:
                MockGhRepo.return_value.list = AsyncMock(return_value=[])
                MockZoneRepo.return_value.list = AsyncMock(return_value=[])

                response = await client.get(
                    f"/api/groups/{group_id}/plant-batches"
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.anyio
    async def test_create_batch_success(self, client: AsyncClient) -> None:
        """POST /api/groups/{group_id}/plant-batches creates a batch."""
        group_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        zone_id = uuid.uuid4()
        batch_id = uuid.uuid4()

        mock_session = _make_mock_session()
        zone = _make_mock_zone(zone_id=zone_id, greenhouse_id=gh_id)
        greenhouse = _make_mock_greenhouse(
            greenhouse_id=gh_id, group_id=group_id
        )
        batch = _make_mock_plant_batch(batch_id=batch_id, zone_id=zone_id)

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch(
                "app.api.plants.ZoneRepository"
            ) as MockZoneRepo, patch(
                "app.api.plants.GreenhouseRepository"
            ) as MockGhRepo, patch(
                "app.api.plants.PlantBatchRepository"
            ) as MockBatchRepo:
                MockZoneRepo.return_value.get_by_id = AsyncMock(
                    return_value=zone
                )
                MockGhRepo.return_value.get_by_id = AsyncMock(
                    return_value=greenhouse
                )
                MockBatchRepo.return_value.create = AsyncMock(
                    return_value=batch
                )

                payload = {
                    "zone_id": str(zone_id),
                    "name": "Summer Tomatoes",
                    "species": "Tomato",
                    "cultivar": "Roma",
                }
                response = await client.post(
                    f"/api/groups/{group_id}/plant-batches",
                    json=payload,
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Batch"  # from _make_mock_plant_batch
        assert data["species"] == "Tomato"
        assert data["profile_id"] is None

    @pytest.mark.anyio
    async def test_create_batch_with_profile_id(self, client: AsyncClient) -> None:
        """POST persists an explicit plant profile link."""
        group_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        zone_id = uuid.uuid4()
        profile_id = uuid.uuid4()

        mock_session = _make_mock_session()
        zone = _make_mock_zone(zone_id=zone_id, greenhouse_id=gh_id)
        greenhouse = _make_mock_greenhouse(greenhouse_id=gh_id, group_id=group_id)
        profile = _make_mock_plant_profile(profile_id=profile_id)
        batch = _make_mock_plant_batch(zone_id=zone_id)
        batch.profile_id = profile_id

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__("app.dependencies", fromlist=["get_db_session"]).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch("app.api.plants.ZoneRepository") as MockZoneRepo, patch(
                "app.api.plants.GreenhouseRepository"
            ) as MockGhRepo, patch(
                "app.api.plants.PlantProfileRepository"
            ) as MockProfileRepo, patch(
                "app.api.plants.PlantBatchRepository"
            ) as MockBatchRepo:
                MockZoneRepo.return_value.get_by_id = AsyncMock(return_value=zone)
                MockGhRepo.return_value.get_by_id = AsyncMock(return_value=greenhouse)
                MockProfileRepo.return_value.get_by_id = AsyncMock(return_value=profile)
                MockBatchRepo.return_value.create = AsyncMock(return_value=batch)

                response = await client.post(
                    f"/api/groups/{group_id}/plant-batches",
                    json={
                        "zone_id": str(zone_id),
                        "profile_id": str(profile_id),
                        "name": "Summer Tomatoes",
                        "species": "Tomato",
                        "growth_stage": "seedling",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        assert response.json()["profile_id"] == str(profile_id)
        MockBatchRepo.return_value.create.assert_awaited_once_with(
            zone_id=zone_id,
            profile_id=profile_id,
            name="Summer Tomatoes",
            species="Tomato",
            cultivar=None,
            planted_at=None,
            growth_stage="seedling",
            notes=None,
        )

    @pytest.mark.anyio
    async def test_create_batch_rejects_missing_profile_id(self, client: AsyncClient) -> None:
        """POST rejects a dangling profile ID."""
        group_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        zone_id = uuid.uuid4()
        profile_id = uuid.uuid4()

        mock_session = _make_mock_session()
        zone = _make_mock_zone(zone_id=zone_id, greenhouse_id=gh_id)
        greenhouse = _make_mock_greenhouse(greenhouse_id=gh_id, group_id=group_id)

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__("app.dependencies", fromlist=["get_db_session"]).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch("app.api.plants.ZoneRepository") as MockZoneRepo, patch(
                "app.api.plants.GreenhouseRepository"
            ) as MockGhRepo, patch(
                "app.api.plants.PlantProfileRepository"
            ) as MockProfileRepo:
                MockZoneRepo.return_value.get_by_id = AsyncMock(return_value=zone)
                MockGhRepo.return_value.get_by_id = AsyncMock(return_value=greenhouse)
                MockProfileRepo.return_value.get_by_id = AsyncMock(return_value=None)

                response = await client.post(
                    f"/api/groups/{group_id}/plant-batches",
                    json={
                        "zone_id": str(zone_id),
                        "profile_id": str(profile_id),
                        "name": "Summer Tomatoes",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_create_batch_zone_not_found(self, client: AsyncClient) -> None:
        """POST returns 404 when zone does not exist."""
        group_id = uuid.uuid4()
        zone_id = uuid.uuid4()

        mock_session = _make_mock_session()

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch(
                "app.api.plants.ZoneRepository"
            ) as MockZoneRepo:
                MockZoneRepo.return_value.get_by_id = AsyncMock(
                    return_value=None
                )

                payload = {
                    "zone_id": str(zone_id),
                    "name": "Test Batch",
                }
                response = await client.post(
                    f"/api/groups/{group_id}/plant-batches",
                    json=payload,
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_get_batch_not_found(self, client: AsyncClient) -> None:
        """GET returns 404 when batch does not exist."""
        group_id = uuid.uuid4()
        batch_id = uuid.uuid4()

        mock_session = _make_mock_session()

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch(
                "app.api.plants.PlantBatchRepository"
            ) as MockBatchRepo:
                MockBatchRepo.return_value.get_by_id = AsyncMock(
                    return_value=None
                )

                response = await client.get(
                    f"/api/groups/{group_id}/plant-batches/{batch_id}"
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_get_batch_success(self, client: AsyncClient) -> None:
        """GET returns batch details."""
        group_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        zone_id = uuid.uuid4()
        batch_id = uuid.uuid4()

        mock_session = _make_mock_session()
        zone = _make_mock_zone(zone_id=zone_id, greenhouse_id=gh_id)
        greenhouse = _make_mock_greenhouse(
            greenhouse_id=gh_id, group_id=group_id
        )
        batch = _make_mock_plant_batch(batch_id=batch_id, zone_id=zone_id)

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch(
                "app.api.plants.PlantBatchRepository"
            ) as MockBatchRepo, patch(
                "app.api.plants.ZoneRepository"
            ) as MockZoneRepo, patch(
                "app.api.plants.GreenhouseRepository"
            ) as MockGhRepo:
                MockBatchRepo.return_value.get_by_id = AsyncMock(
                    return_value=batch
                )
                MockZoneRepo.return_value.get_by_id = AsyncMock(
                    return_value=zone
                )
                MockGhRepo.return_value.get_by_id = AsyncMock(
                    return_value=greenhouse
                )

                response = await client.get(
                    f"/api/groups/{group_id}/plant-batches/{batch_id}"
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Batch"

    @pytest.mark.anyio
    async def test_update_batch_success(self, client: AsyncClient) -> None:
        """PATCH updates batch metadata."""
        group_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        zone_id = uuid.uuid4()
        batch_id = uuid.uuid4()

        mock_session = _make_mock_session()
        zone = _make_mock_zone(zone_id=zone_id, greenhouse_id=gh_id)
        greenhouse = _make_mock_greenhouse(
            greenhouse_id=gh_id, group_id=group_id
        )
        batch = _make_mock_plant_batch(batch_id=batch_id, zone_id=zone_id)

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__(
                "app.dependencies", fromlist=["get_db_session"]
            ).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch(
                "app.api.plants.PlantBatchRepository"
            ) as MockBatchRepo, patch(
                "app.api.plants.ZoneRepository"
            ) as MockZoneRepo, patch(
                "app.api.plants.GreenhouseRepository"
            ) as MockGhRepo:
                MockBatchRepo.return_value.get_by_id = AsyncMock(
                    return_value=batch
                )
                MockBatchRepo.return_value.update = AsyncMock(
                    return_value=batch
                )
                MockZoneRepo.return_value.get_by_id = AsyncMock(
                    return_value=zone
                )
                MockGhRepo.return_value.get_by_id = AsyncMock(
                    return_value=greenhouse
                )

                payload = {"name": "Updated Batch Name"}
                response = await client.patch(
                    f"/api/groups/{group_id}/plant-batches/{batch_id}",
                    json=payload,
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_update_batch_profile_id(self, client: AsyncClient) -> None:
        """PATCH can attach a profile to an existing plant batch."""
        group_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        zone_id = uuid.uuid4()
        batch_id = uuid.uuid4()
        profile_id = uuid.uuid4()

        mock_session = _make_mock_session()
        zone = _make_mock_zone(zone_id=zone_id, greenhouse_id=gh_id)
        greenhouse = _make_mock_greenhouse(greenhouse_id=gh_id, group_id=group_id)
        profile = _make_mock_plant_profile(profile_id=profile_id)
        batch = _make_mock_plant_batch(batch_id=batch_id, zone_id=zone_id)
        batch.profile_id = profile_id

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__("app.dependencies", fromlist=["get_db_session"]).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch("app.api.plants.PlantBatchRepository") as MockBatchRepo, patch(
                "app.api.plants.ZoneRepository"
            ) as MockZoneRepo, patch(
                "app.api.plants.GreenhouseRepository"
            ) as MockGhRepo, patch(
                "app.api.plants.PlantProfileRepository"
            ) as MockProfileRepo:
                MockBatchRepo.return_value.get_by_id = AsyncMock(return_value=batch)
                MockBatchRepo.return_value.update = AsyncMock(return_value=batch)
                MockZoneRepo.return_value.get_by_id = AsyncMock(return_value=zone)
                MockGhRepo.return_value.get_by_id = AsyncMock(return_value=greenhouse)
                MockProfileRepo.return_value.get_by_id = AsyncMock(return_value=profile)

                response = await client.patch(
                    f"/api/groups/{group_id}/plant-batches/{batch_id}",
                    json={"profile_id": str(profile_id)},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["profile_id"] == str(profile_id)
        MockBatchRepo.return_value.update.assert_awaited_once_with(batch_id, profile_id=profile_id)
        mock_session.commit.assert_awaited_once()

    @pytest.mark.anyio
    async def test_update_batch_detaches_profile_id(self, client: AsyncClient) -> None:
        """PATCH can clear a plant batch profile link."""
        group_id = uuid.uuid4()
        gh_id = uuid.uuid4()
        zone_id = uuid.uuid4()
        batch_id = uuid.uuid4()

        mock_session = _make_mock_session()
        zone = _make_mock_zone(zone_id=zone_id, greenhouse_id=gh_id)
        greenhouse = _make_mock_greenhouse(greenhouse_id=gh_id, group_id=group_id)
        batch = _make_mock_plant_batch(batch_id=batch_id, zone_id=zone_id)
        batch.profile_id = None

        async def override_session():
            yield mock_session

        app.dependency_overrides[
            __import__("app.dependencies", fromlist=["get_db_session"]).get_db_session
        ] = override_session

        try:
            from unittest.mock import patch

            with patch("app.api.plants.PlantBatchRepository") as MockBatchRepo, patch(
                "app.api.plants.ZoneRepository"
            ) as MockZoneRepo, patch(
                "app.api.plants.GreenhouseRepository"
            ) as MockGhRepo:
                MockBatchRepo.return_value.get_by_id = AsyncMock(return_value=batch)
                MockBatchRepo.return_value.update = AsyncMock(return_value=batch)
                MockZoneRepo.return_value.get_by_id = AsyncMock(return_value=zone)
                MockGhRepo.return_value.get_by_id = AsyncMock(return_value=greenhouse)

                response = await client.patch(
                    f"/api/groups/{group_id}/plant-batches/{batch_id}",
                    json={"profile_id": None},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["profile_id"] is None
        MockBatchRepo.return_value.update.assert_awaited_once_with(batch_id, profile_id=None)
