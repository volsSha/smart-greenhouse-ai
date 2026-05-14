"""Tests for model settings repository refresh behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.model_settings_repository import ModelSettingsRepository


@pytest.mark.anyio
async def test_record_refresh_success_bulk_deletes_catalog_before_inserting() -> None:
    session = MagicMock(spec=AsyncSession)
    settings = SimpleNamespace(
        selected_chat_model=None,
        last_refresh_at=None,
        last_refresh_status=None,
        last_refresh_error="previous error",
        selected_model_available=False,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = settings
    session.execute = AsyncMock(side_effect=[result, MagicMock()])
    session.add = MagicMock()
    session.flush = AsyncMock()

    repo = ModelSettingsRepository(session)
    rows = await repo.record_refresh_success([
        {
            "model_id": "test/model",
            "name": "Test Model",
            "provider": "test",
            "capabilities": None,
            "prompt_price_per_million": 1.0,
            "completion_price_per_million": 2.0,
            "context_length": 4096,
            "max_completion_tokens": 1024,
            "raw_metadata": {"id": "test/model"},
        }
    ])

    assert len(rows) == 1
    assert session.execute.await_count == 2
    assert str(session.execute.await_args_list[1].args[0]).startswith("DELETE FROM openrouter_model_catalog")
    session.add.assert_called_once()
    session.flush.assert_awaited_once()
