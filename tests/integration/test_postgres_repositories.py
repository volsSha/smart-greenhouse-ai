"""Tests for repository layer using mocked async sessions.

Since we may not have a running PostgreSQL instance available in CI,
these tests mock the AsyncSession to verify repository method signatures,
argument handling, and basic plumbing without real database I/O.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Alert,
    Greenhouse,
    GreenhouseGroup,
    GreenhouseZone,
)
from app.repositories.alert_repository import AlertRepository
from app.repositories.device_repository import ActuatorRepository, EdgeNodeRepository, SensorRepository
from app.repositories.greenhouse_repository import GreenhouseRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.zone_repository import ZoneRepository


def _make_mock_session() -> AsyncSession:
    """Create a mock AsyncSession with async methods."""
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def _make_model_instance(model_class, **overrides):
    """Create a lightweight mock stand-in for a model instance."""
    defaults = {"id": uuid.uuid4()}
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# GroupRepository
# ---------------------------------------------------------------------------

class TestGroupRepository:
    """Tests for GroupRepository with mock session."""

    @pytest.mark.asyncio
    async def test_create_calls_add_and_flush(self):
        session = _make_mock_session()
        repo = GroupRepository(session)

        group = await repo.create(name="Test Farm", location="Berlin")

        assert session.add.called
        assert session.flush.called
        assert group.name == "Test Farm"

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_missing(self):
        session = _make_mock_session()
        repo = GroupRepository(session)

        result = await repo.get_by_id(uuid.uuid4())

        assert result is None
        session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_returns_instance_when_found(self):
        session = _make_mock_session()
        fake_id = uuid.uuid4()
        fake_group = _make_model_instance(GreenhouseGroup, name="Found")
        session.get = AsyncMock(return_value=fake_group)
        repo = GroupRepository(session)

        result = await repo.get_by_id(fake_id)

        assert result is fake_group

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_missing(self):
        session = _make_mock_session()
        repo = GroupRepository(session)

        result = await repo.delete(uuid.uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_found(self):
        session = _make_mock_session()
        fake_group = _make_model_instance(GreenhouseGroup)
        session.get = AsyncMock(return_value=fake_group)
        repo = GroupRepository(session)

        result = await repo.delete(fake_group.id)

        assert result is True
        session.delete.assert_called_once()


# ---------------------------------------------------------------------------
# GreenhouseRepository
# ---------------------------------------------------------------------------

class TestGreenhouseRepository:
    """Tests for GreenhouseRepository with mock session."""

    @pytest.mark.asyncio
    async def test_create_with_group_id(self):
        session = _make_mock_session()
        repo = GreenhouseRepository(session)
        group_id = uuid.uuid4()

        greenhouse = await repo.create(group_id=group_id, name="GH-1")

        assert session.add.called
        assert greenhouse.name == "GH-1"
        assert greenhouse.group_id == group_id

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_session_get(self):
        session = _make_mock_session()
        repo = GreenhouseRepository(session)
        gh_id = uuid.uuid4()

        await repo.get_by_id(gh_id)

        session.get.assert_called_once_with(Greenhouse, gh_id)


# ---------------------------------------------------------------------------
# ZoneRepository
# ---------------------------------------------------------------------------

class TestZoneRepository:
    """Tests for ZoneRepository with mock session."""

    @pytest.mark.asyncio
    async def test_create_with_greenhouse_id(self):
        session = _make_mock_session()
        repo = ZoneRepository(session)
        gh_id = uuid.uuid4()

        zone = await repo.create(greenhouse_id=gh_id, name="Zone A")

        assert session.add.called
        assert zone.greenhouse_id == gh_id

    @pytest.mark.asyncio
    async def test_update_modifies_attributes(self):
        session = _make_mock_session()
        fake_zone = _make_model_instance(GreenhouseZone, name="Old Name")
        session.get = AsyncMock(return_value=fake_zone)
        repo = ZoneRepository(session)

        result = await repo.update(fake_zone.id, name="New Name")

        assert result is fake_zone
        assert result.name == "New Name"
        session.flush.assert_called_once()


# ---------------------------------------------------------------------------
# EdgeNodeRepository
# ---------------------------------------------------------------------------

class TestEdgeNodeRepository:
    """Tests for EdgeNodeRepository with mock session."""

    @pytest.mark.asyncio
    async def test_create_sets_all_fields(self):
        session = _make_mock_session()
        repo = EdgeNodeRepository(session)
        gh_id = uuid.uuid4()

        node = await repo.create(
            greenhouse_id=gh_id,
            node_key="esp-001",
            name="ESP32 Main",
            node_type="esp32",
            firmware_version="1.2.0",
        )

        assert node.node_key == "esp-001"
        assert node.node_type == "esp32"

    @pytest.mark.asyncio
    async def test_get_by_node_key_executes_query(self):
        session = _make_mock_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        repo = EdgeNodeRepository(session)

        result = await repo.get_by_node_key("esp-001")

        assert result is None
        session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# SensorRepository / ActuatorRepository
# ---------------------------------------------------------------------------

class TestSensorRepository:
    """Tests for SensorRepository with mock session."""

    @pytest.mark.asyncio
    async def test_create_sensor(self):
        session = _make_mock_session()
        repo = SensorRepository(session)
        zone_id = uuid.uuid4()

        sensor = await repo.create(
            zone_id=zone_id,
            sensor_key="temp-01",
            metric="temperature",
            unit="celsius",
        )

        assert sensor.sensor_key == "temp-01"
        assert sensor.metric == "temperature"


class TestActuatorRepository:
    """Tests for ActuatorRepository with mock session."""

    @pytest.mark.asyncio
    async def test_create_actuator(self):
        session = _make_mock_session()
        repo = ActuatorRepository(session)
        zone_id = uuid.uuid4()

        actuator = await repo.create(
            zone_id=zone_id,
            actuator_key="pump-01",
            actuator_type="pump",
        )

        assert actuator.actuator_key == "pump-01"
        assert actuator.actuator_type == "pump"


# ---------------------------------------------------------------------------
# AlertRepository
# ---------------------------------------------------------------------------

class TestAlertRepository:
    """Tests for AlertRepository with mock session."""

    @pytest.mark.asyncio
    async def test_create_alert(self):
        session = _make_mock_session()
        repo = AlertRepository(session)
        group_id = uuid.uuid4()

        alert = await repo.create(
            group_id=group_id,
            severity="warning",
            title="High Temperature",
            message="Temperature exceeded 35C",
            source="threshold",
        )

        assert alert.severity == "warning"
        assert alert.status == "active"

    @pytest.mark.asyncio
    async def test_list_by_status_convenience_method(self):
        session = _make_mock_session()
        repo = AlertRepository(session)

        # Mock the execute result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        await repo.list_by_status("active")

        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_alert_status(self):
        session = _make_mock_session()
        fake_alert = _make_model_instance(Alert, status="active")
        session.get = AsyncMock(return_value=fake_alert)
        repo = AlertRepository(session)

        result = await repo.update(fake_alert.id, status="resolved")

        assert result.status == "resolved"
