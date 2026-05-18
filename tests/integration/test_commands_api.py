"""Integration tests for the commands API endpoints.

Tests use FastAPI dependency overrides to inject mock sessions,
avoiding the need for a running database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.schemas.commands import CommandPropose
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.commands import get_command_publisher, get_db_session, router as commands_router


# --- Build a minimal test app with just the commands router ---
from fastapi import FastAPI

cmd_test_app = FastAPI()
cmd_test_app.include_router(commands_router)


def _make_fake_command(**overrides) -> SimpleNamespace:
    """Create a lightweight fake CommandLog for API responses."""
    defaults = {
        "id": uuid.uuid4(),
        "group_id": uuid.uuid4(),
        "greenhouse_id": uuid.uuid4(),
        "zone_id": uuid.uuid4(),
        "actuator_id": None,
        "actuator_name": "pump",
        "action": "on",
        "value": None,
        "unit": None,
        "duration_seconds": 30,
        "source": "manual",
        "reason": None,
        "validation_errors": None,
        "status": "validated",
        "valid_until": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "mode": "mqtt",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


async def _publisher_override():
    publisher = MagicMock()
    publisher.publish = AsyncMock(return_value={"topic": "commands", "payload": {}})
    yield publisher


def _make_mock_session() -> MagicMock:
    """Create a mock AsyncSession."""
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    session.close = AsyncMock()
    return session


def _make_propose_payload(
    actuator: str = "pump",
    action: str = "on",
    duration_seconds: int = 30,
) -> dict:
    """Create a JSON payload for the propose endpoint."""
    return {
        "group_id": str(uuid.uuid4()),
        "greenhouse_id": str(uuid.uuid4()),
        "zone_id": str(uuid.uuid4()),
        "actuator": actuator,
        "action": action,
        "duration_seconds": duration_seconds,
        "source": "manual",
    }


class TestProposeEndpoint:
    """Tests for POST /api/commands/propose."""

    @pytest.mark.anyio
    async def test_propose_returns_201(self) -> None:
        """Proposing a valid command returns 201 with validated status."""
        fake_cmd = _make_fake_command(status="validated")
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        cmd_test_app.dependency_overrides[get_db_session] = _session_override
        cmd_test_app.dependency_overrides[get_command_publisher] = _publisher_override

        with (
            patch("app.api.commands.ModelSettingsRepository") as MockSettingsRepo,
            patch(
                "app.services.command_service.CommandRepository.create",
                new_callable=AsyncMock,
                return_value=fake_cmd,
            ),
            patch(
                "app.services.command_service.CommandRepository.update_status",
                new_callable=AsyncMock,
                return_value=_make_fake_command(status="validated"),
            ),
        ):
            MockSettingsRepo.return_value.bootstrap_settings = AsyncMock(return_value=SimpleNamespace(control_mode="mqtt"))
            transport = ASGITransport(app=cmd_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/commands/propose",
                    json=_make_propose_payload(),
                )

        cmd_test_app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "validated"
        assert data["actuator_name"] == "pump"

    @pytest.mark.anyio
    async def test_propose_invalid_returns_201_with_errors(self) -> None:
        """Proposing an invalid command returns 201 but with validation errors."""
        fake_cmd = _make_fake_command(
            actuator_name="heater",
            action="on",
            duration_seconds=600,
            status="proposed",
            validation_errors={
                "errors": ["Duration 600s exceeds maximum 300s"],
                "warnings": [],
            },
        )
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        cmd_test_app.dependency_overrides[get_db_session] = _session_override
        cmd_test_app.dependency_overrides[get_command_publisher] = _publisher_override

        with (
            patch("app.api.commands.ModelSettingsRepository") as MockSettingsRepo,
            patch(
                "app.services.command_service.CommandRepository.create",
                new_callable=AsyncMock,
                return_value=fake_cmd,
            ),
            patch(
                "app.services.command_service.CommandRepository.update_status",
                new_callable=AsyncMock,
                return_value=fake_cmd,
            ),
        ):
            MockSettingsRepo.return_value.bootstrap_settings = AsyncMock(return_value=SimpleNamespace(control_mode="mqtt"))
            transport = ASGITransport(app=cmd_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/commands/propose",
                    json=_make_propose_payload(
                        actuator="heater",
                        action="on",
                        duration_seconds=600,
                    ),
                )

        cmd_test_app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "proposed"
        assert data["validation_errors"] is not None

    @pytest.mark.anyio
    async def test_propose_uses_persisted_mode_over_payload_mode(self) -> None:
        mock_session = _make_mock_session()
        captured: dict[str, CommandPropose] = {}

        async def _session_override():
            yield mock_session

        async def _capture_propose(self, data: CommandPropose):
            captured["data"] = data
            return _make_fake_command(status="validated", mode=data.mode)

        cmd_test_app.dependency_overrides[get_db_session] = _session_override
        cmd_test_app.dependency_overrides[get_command_publisher] = _publisher_override

        payload = _make_propose_payload()
        payload["mode"] = "mqtt"

        with (
            patch("app.api.commands.ModelSettingsRepository") as MockSettingsRepo,
            patch("app.api.commands.CommandService.propose", new=_capture_propose),
        ):
            MockSettingsRepo.return_value.bootstrap_settings = AsyncMock(return_value=SimpleNamespace(control_mode="simulator"))
            transport = ASGITransport(app=cmd_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/commands/propose", json=payload)

        cmd_test_app.dependency_overrides.clear()

        assert response.status_code == 201
        assert captured["data"].mode == "simulator"
        assert response.json()["mode"] == "simulator"


class TestApproveEndpoint:
    """Tests for POST /api/commands/{id}/approve."""

    @pytest.mark.anyio
    async def test_approve_returns_200(self) -> None:
        """Approving a valid command returns 200."""
        fake_cmd = _make_fake_command(status="validated")
        mock_session = _make_mock_session()
        mock_session.get = AsyncMock(return_value=fake_cmd)

        async def _session_override():
            yield mock_session

        cmd_test_app.dependency_overrides[get_db_session] = _session_override
        cmd_test_app.dependency_overrides[get_command_publisher] = _publisher_override

        with (
            patch(
                "app.services.command_service.CommandRepository.update_status",
                new_callable=AsyncMock,
                side_effect=[
                    _make_fake_command(status="approved"),
                    _make_fake_command(status="executing"),
                    _make_fake_command(status="executed"),
                ],
            ),
        ):
            transport = ASGITransport(app=cmd_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/commands/{fake_cmd.id}/approve",
                )

        cmd_test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "executed"

    @pytest.mark.anyio
    async def test_approve_nonexistent_returns_409(self) -> None:
        """Approving a non-existent command returns 409."""
        mock_session = _make_mock_session()
        mock_session.get = AsyncMock(return_value=None)

        async def _session_override():
            yield mock_session

        cmd_test_app.dependency_overrides[get_db_session] = _session_override
        cmd_test_app.dependency_overrides[get_command_publisher] = _publisher_override

        transport = ASGITransport(app=cmd_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/commands/{uuid.uuid4()}/approve",
            )

        cmd_test_app.dependency_overrides.clear()

        assert response.status_code == 409


class TestCancelEndpoint:
    """Tests for POST /api/commands/{id}/cancel."""

    @pytest.mark.anyio
    async def test_cancel_returns_200(self) -> None:
        """Cancelling a command returns 200."""
        fake_cmd = _make_fake_command(status="proposed")
        mock_session = _make_mock_session()
        mock_session.get = AsyncMock(return_value=fake_cmd)

        async def _session_override():
            yield mock_session

        cmd_test_app.dependency_overrides[get_db_session] = _session_override
        cmd_test_app.dependency_overrides[get_command_publisher] = _publisher_override

        with (
            patch(
                "app.services.command_service.CommandRepository.update_status",
                new_callable=AsyncMock,
                return_value=_make_fake_command(status="cancelled"),
            ),
        ):
            transport = ASGITransport(app=cmd_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/commands/{fake_cmd.id}/cancel",
                )

        cmd_test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.anyio
    async def test_cancel_executed_returns_409(self) -> None:
        """Cancelling an executed command returns 409 (invalid transition)."""
        fake_cmd = _make_fake_command(status="executed")
        mock_session = _make_mock_session()
        mock_session.get = AsyncMock(return_value=fake_cmd)

        async def _session_override():
            yield mock_session

        cmd_test_app.dependency_overrides[get_db_session] = _session_override
        cmd_test_app.dependency_overrides[get_command_publisher] = _publisher_override

        transport = ASGITransport(app=cmd_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/commands/{fake_cmd.id}/cancel",
            )

        cmd_test_app.dependency_overrides.clear()

        assert response.status_code == 409


class TestRecentCommandsEndpoint:
    """Tests for GET /api/commands/groups/{group_id}/recent."""

    @pytest.mark.anyio
    async def test_recent_returns_200(self) -> None:
        """Listing recent commands returns 200."""
        group_id = uuid.uuid4()
        fake_commands = [
            _make_fake_command(status="executed"),
            _make_fake_command(status="approved"),
        ]
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        cmd_test_app.dependency_overrides[get_db_session] = _session_override
        cmd_test_app.dependency_overrides[get_command_publisher] = _publisher_override

        with (
            patch(
                "app.services.command_service.CommandRepository.get_recent",
                new_callable=AsyncMock,
                return_value=fake_commands,
            ),
        ):
            transport = ASGITransport(app=cmd_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/commands/groups/{group_id}/recent",
                )

        cmd_test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.anyio
    async def test_recent_empty_returns_empty_list(self) -> None:
        """Listing recent commands with no results returns empty list."""
        group_id = uuid.uuid4()
        mock_session = _make_mock_session()

        async def _session_override():
            yield mock_session

        cmd_test_app.dependency_overrides[get_db_session] = _session_override
        cmd_test_app.dependency_overrides[get_command_publisher] = _publisher_override

        with (
            patch(
                "app.services.command_service.CommandRepository.get_recent",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            transport = ASGITransport(app=cmd_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/commands/groups/{group_id}/recent",
                )

        cmd_test_app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data == []
