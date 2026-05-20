"""Integration tests for persisted alert endpoints."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.main import app


def _make_mock_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


def _make_alert(
    *,
    alert_id: uuid.UUID | None = None,
    group_id: uuid.UUID | None = None,
    status: str = "active",
    created_at: datetime | None = None,
) -> MagicMock:
    alert = MagicMock()
    alert.id = alert_id or uuid.uuid4()
    alert.group_id = group_id or uuid.uuid4()
    alert.greenhouse_id = uuid.uuid4()
    alert.zone_id = uuid.uuid4()
    alert.metric = "temperature"
    alert.severity = "critical"
    alert.title = "Temperature too high"
    alert.message = "Zone temperature exceeded the safe threshold."
    alert.status = status
    alert.source = "threshold"
    alert.created_at = created_at or datetime.now(timezone.utc)
    alert.resolved_at = None
    return alert


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
def mock_session() -> AsyncMock:
    return _make_mock_session()


async def _override_session(session: AsyncMock):
    async def override():
        yield session

    app.dependency_overrides[get_db_session] = override


class TestAlertsAPI:
    @pytest.mark.anyio
    async def test_list_active_alerts_for_group(self, client: AsyncClient, mock_session: AsyncMock) -> None:
        group_id = uuid.uuid4()
        newest = _make_alert(group_id=group_id, created_at=datetime(2026, 5, 20, 12, 1, tzinfo=timezone.utc))
        older = _make_alert(group_id=group_id, created_at=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc))
        await _override_session(mock_session)

        try:
            with patch("app.api.alerts.AlertRepository") as MockRepo:
                MockRepo.return_value.list_by_group = AsyncMock(return_value=[newest, older])
                response = await client.get(f"/api/groups/{group_id}/alerts?status=active")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert [row["id"] for row in data] == [str(newest.id), str(older.id)]
        assert data[0]["title"] == "Temperature too high"
        assert data[0]["message"] == "Zone temperature exceeded the safe threshold."
        MockRepo.return_value.list_by_group.assert_awaited_once_with(group_id, status="active")

    @pytest.mark.anyio
    async def test_list_alerts_limits_results(self, client: AsyncClient, mock_session: AsyncMock) -> None:
        group_id = uuid.uuid4()
        alerts = [_make_alert(group_id=group_id) for _ in range(3)]
        await _override_session(mock_session)

        try:
            with patch("app.api.alerts.AlertRepository") as MockRepo:
                MockRepo.return_value.list_by_group = AsyncMock(return_value=alerts)
                response = await client.get(f"/api/groups/{group_id}/alerts?status=active&limit=2")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.anyio
    async def test_list_rejects_unsupported_status_filter(self, client: AsyncClient, mock_session: AsyncMock) -> None:
        group_id = uuid.uuid4()
        await _override_session(mock_session)

        try:
            response = await client.get(f"/api/groups/{group_id}/alerts?status=anything")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_dismiss_alert_commits_status_update(self, client: AsyncClient, mock_session: AsyncMock) -> None:
        group_id = uuid.uuid4()
        alert_id = uuid.uuid4()
        alert = _make_alert(alert_id=alert_id, group_id=group_id)
        dismissed = _make_alert(alert_id=alert_id, group_id=group_id, status="dismissed")
        await _override_session(mock_session)

        try:
            with patch("app.api.alerts.AlertRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_by_id = AsyncMock(return_value=alert)
                mock_repo.update = AsyncMock(return_value=dismissed)
                response = await client.patch(
                    f"/api/groups/{group_id}/alerts/{alert_id}",
                    json={"status": "dismissed"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["status"] == "dismissed"
        mock_repo.update.assert_awaited_once_with(alert_id, status="dismissed")
        mock_session.commit.assert_awaited_once()

    @pytest.mark.anyio
    async def test_dismiss_rejects_cross_group_alert(self, client: AsyncClient, mock_session: AsyncMock) -> None:
        group_id = uuid.uuid4()
        alert_id = uuid.uuid4()
        alert = _make_alert(alert_id=alert_id, group_id=uuid.uuid4())
        await _override_session(mock_session)

        try:
            with patch("app.api.alerts.AlertRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get_by_id = AsyncMock(return_value=alert)
                mock_repo.update = AsyncMock()
                response = await client.patch(
                    f"/api/groups/{group_id}/alerts/{alert_id}",
                    json={"status": "dismissed"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404
        mock_repo.update.assert_not_awaited()
        mock_session.commit.assert_not_awaited()

    @pytest.mark.anyio
    async def test_dismiss_rejects_non_dismissed_status(self, client: AsyncClient, mock_session: AsyncMock) -> None:
        group_id = uuid.uuid4()
        alert_id = uuid.uuid4()
        await _override_session(mock_session)

        try:
            response = await client.patch(
                f"/api/groups/{group_id}/alerts/{alert_id}",
                json={"status": "resolved"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422
