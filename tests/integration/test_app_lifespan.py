"""Integration tests for app lifespan and route registration.

Tests that the FastAPI application initializes correctly with
dependency overrides, and that expected routes exist.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


class TestAppLifespan:
    """Tests for the application lifespan context manager."""

    @pytest.mark.anyio
    async def test_app_starts_with_mocked_dependencies(self) -> None:
        """App starts successfully when DB/InfluxDB are mocked."""
        from app.main import app, lifespan

        # Create a mock engine
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        # Create a mock InfluxDB client
        mock_influx = MagicMock()
        mock_influx.close = MagicMock()

        # Patch the factory functions
        with (
            patch("app.main.create_db_engine", return_value=mock_engine),
            patch("app.main.create_influx_client", return_value=mock_influx),
        ):
            async with lifespan(app):
                # Verify state was populated
                assert hasattr(app.state, "settings")
                assert hasattr(app.state, "db_engine")
                assert hasattr(app.state, "session_factory")
                assert hasattr(app.state, "influx_client")

                # Verify engine is the mock
                assert app.state.db_engine is mock_engine
                assert app.state.influx_client is mock_influx

            # After exit, dispose should have been called
            mock_engine.dispose.assert_awaited_once()
            mock_influx.close.assert_called_once()


class TestRouteRegistration:
    """Tests for expected API routes."""

    def test_health_routes_exist(self) -> None:
        """Health check routes are registered on the app."""
        from app.main import app

        route_paths = {route.path for route in app.routes}
        assert "/api/health/live" in route_paths
        assert "/api/health/ready" in route_paths

    @pytest.mark.anyio
    async def test_404_for_unknown_route(self) -> None:
        """Unknown routes return 404 via JSON."""
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/api/unknown")

        # NiceGUI handles 404s with HTML, but API routes under /api should
        # return JSON. Since /api/unknown is not registered, FastAPI returns 404.
        assert response.status_code == 404
