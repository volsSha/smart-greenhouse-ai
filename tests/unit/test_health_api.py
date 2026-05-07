"""Tests for the health check API endpoints."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestLivenessEndpoint:
    """Tests for GET /api/health/live."""

    @pytest.fixture()
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        """Create a test client without starting the full lifespan."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as ac:
            yield ac

    @pytest.mark.anyio
    async def test_live_returns_200(self, client: AsyncClient) -> None:
        """Liveness probe always returns 200 with status 'alive'."""
        response = await client.get("/api/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


def _setup_mock_db_engine(should_fail: bool = False) -> MagicMock:
    """Create a mock async database engine."""
    mock_conn = AsyncMock()
    if should_fail:
        mock_conn.execute = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )
    else:
        mock_conn.execute = AsyncMock()

    engine = MagicMock()
    engine.connect = MagicMock(return_value=mock_conn)
    engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
    return engine


def _setup_mock_influx(should_fail: bool = False) -> MagicMock:
    """Create a mock InfluxDB client."""
    client = MagicMock()
    health_mock = MagicMock()
    if should_fail:
        health_mock.status = "fail"
    else:
        health_mock.status = "pass"
    client.health = MagicMock(return_value=health_mock)
    return client


def _setup_mock_settings() -> MagicMock:
    """Create mock settings for MQTT."""
    settings = MagicMock()
    settings.mqtt.host = "localhost"
    settings.mqtt.port = 1883
    settings.mqtt.username = ""
    settings.mqtt.password = ""
    return settings


class TestReadinessEndpoint:
    """Tests for GET /api/health/ready."""

    @pytest.mark.anyio
    async def test_ready_returns_200_when_all_healthy(self) -> None:
        """Readiness returns 200 when all components are healthy."""
        mock_engine = _setup_mock_db_engine()
        mock_influx = _setup_mock_influx()
        mock_settings = _setup_mock_settings()

        app.state.db_engine = mock_engine  # type: ignore[attr-defined]
        app.state.influx_client = mock_influx  # type: ignore[attr-defined]
        app.state.settings = mock_settings  # type: ignore[attr-defined]

        with (
            patch("aiomqtt.Client.__aenter__", new_callable=AsyncMock, return_value=None),
            patch("aiomqtt.Client.__aexit__", new_callable=AsyncMock, return_value=False),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.get("/api/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        component_names = {c["name"] for c in data["components"]}
        assert component_names == {"database", "influxdb", "mqtt"}
        assert all(c["healthy"] for c in data["components"])

    @pytest.mark.anyio
    async def test_ready_returns_503_when_database_fails(self) -> None:
        """Readiness returns 503 when the database check fails."""
        mock_engine = _setup_mock_db_engine(should_fail=True)
        mock_influx = _setup_mock_influx()
        mock_settings = _setup_mock_settings()

        app.state.db_engine = mock_engine  # type: ignore[attr-defined]
        app.state.influx_client = mock_influx  # type: ignore[attr-defined]
        app.state.settings = mock_settings  # type: ignore[attr-defined]

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/api/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        db_component = next(c for c in data["components"] if c["name"] == "database")
        assert db_component["healthy"] is False

    @pytest.mark.anyio
    async def test_ready_returns_503_when_influxdb_fails(self) -> None:
        """Readiness returns 503 when InfluxDB health check fails."""
        mock_engine = _setup_mock_db_engine()
        mock_influx = _setup_mock_influx(should_fail=True)
        mock_settings = _setup_mock_settings()

        app.state.db_engine = mock_engine  # type: ignore[attr-defined]
        app.state.influx_client = mock_influx  # type: ignore[attr-defined]
        app.state.settings = mock_settings  # type: ignore[attr-defined]

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/api/health/ready")

        assert response.status_code == 503
        data = response.json()
        influx_component = next(
            c for c in data["components"] if c["name"] == "influxdb"
        )
        assert influx_component["healthy"] is False

    @pytest.mark.anyio
    async def test_ready_returns_503_when_mqtt_fails(self) -> None:
        """Readiness returns 503 when MQTT connection fails."""
        mock_engine = _setup_mock_db_engine()
        mock_influx = _setup_mock_influx()
        mock_settings = _setup_mock_settings()

        app.state.db_engine = mock_engine  # type: ignore[attr-defined]
        app.state.influx_client = mock_influx  # type: ignore[attr-defined]
        app.state.settings = mock_settings  # type: ignore[attr-defined]

        with patch(
            "aiomqtt.Client.__aenter__",
            new_callable=AsyncMock,
            side_effect=ConnectionError("MQTT refused"),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.get("/api/health/ready")

        assert response.status_code == 503
        data = response.json()
        mqtt_component = next(c for c in data["components"] if c["name"] == "mqtt")
        assert mqtt_component["healthy"] is False
