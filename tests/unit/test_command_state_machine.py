"""Unit tests for the command lifecycle state machine.

Tests cover:
- proposed -> validated transition for valid commands
- rejection of invalid commands
- cancel transitions
- expiry of stale commands
- invalid transitions raise CommandError
- approve re-validates and can reject
- execute transitions through executing -> executed
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.commands import CommandPropose
from app.services.command_service import (
    CommandError,
    CommandService,
    CommandStatus,
    _check_transition,
)


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


def _make_command_log(
    command_id: uuid.UUID | None = None,
    status: str = "proposed",
    actuator_name: str = "pump",
    action: str = "on",
    value: float | None = None,
    duration_seconds: int | None = 30,
    valid_until: datetime | None = None,
    mode: str = "mqtt",
) -> SimpleNamespace:
    """Create a lightweight mock CommandLog."""
    return SimpleNamespace(
        id=command_id or uuid.uuid4(),
        group_id=uuid.uuid4(),
        greenhouse_id=uuid.uuid4(),
        zone_id=uuid.uuid4(),
        actuator_id=None,
        actuator_name=actuator_name,
        action=action,
        value=value,
        unit=None,
        duration_seconds=duration_seconds,
        source="manual",
        reason=None,
        validation_errors=None,
        status=status,
        valid_until=valid_until,
        mode=mode,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_proposal(
    actuator: str = "pump",
    action: str = "on",
    duration_seconds: int | None = 30,
) -> CommandPropose:
    """Create a CommandPropose with sensible defaults."""
    return CommandPropose(
        group_id=uuid.uuid4(),
        greenhouse_id=uuid.uuid4(),
        zone_id=uuid.uuid4(),
        actuator=actuator,
        action=action,
        value=None,
        duration_seconds=duration_seconds,
        source="manual",
    )


class TestCheckTransition:
    """Tests for the _check_transition helper."""

    def test_valid_transition_proposed_to_validated(self) -> None:
        _check_transition(CommandStatus.PROPOSED, CommandStatus.VALIDATED)

    def test_valid_transition_validated_to_approved(self) -> None:
        _check_transition(CommandStatus.VALIDATED, CommandStatus.APPROVED)

    def test_valid_transition_approved_to_executing(self) -> None:
        _check_transition(CommandStatus.APPROVED, CommandStatus.EXECUTING)

    def test_valid_transition_executing_to_executed(self) -> None:
        _check_transition(CommandStatus.EXECUTING, CommandStatus.EXECUTED)

    def test_invalid_transition_executed_to_approved(self) -> None:
        with pytest.raises(CommandError, match="Invalid transition"):
            _check_transition(CommandStatus.EXECUTED, CommandStatus.APPROVED)

    def test_invalid_transition_cancelled_to_approved(self) -> None:
        with pytest.raises(CommandError, match="Invalid transition"):
            _check_transition(CommandStatus.CANCELLED, CommandStatus.APPROVED)

    def test_invalid_transition_proposed_to_executing(self) -> None:
        with pytest.raises(CommandError, match="Invalid transition"):
            _check_transition(CommandStatus.PROPOSED, CommandStatus.EXECUTING)


class TestPropose:
    """Tests for CommandService.propose."""

    @pytest.mark.asyncio
    async def test_propose_valid_command_transitions_to_validated(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        # Mock the repo.create to return a SimpleNamespace that mimics CommandLog
        fake_cmd = _make_command_log(status="proposed")
        with patch.object(
            service.repo, "create", new_callable=AsyncMock, return_value=fake_cmd
        ):
            with patch.object(
                service.repo,
                "update_status",
                new_callable=AsyncMock,
                return_value=_make_command_log(status="validated"),
            ):
                command = await service.propose(_make_proposal())

        assert command.status == "validated"

    @pytest.mark.asyncio
    async def test_propose_invalid_command_stays_proposed(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        # Propose a heater with excessive duration
        fake_cmd = _make_command_log(
            actuator_name="heater",
            action="on",
            duration_seconds=600,
            status="proposed",
        )
        with patch.object(
            service.repo, "create", new_callable=AsyncMock, return_value=fake_cmd
        ):
            with patch.object(
                service.repo,
                "update_status",
                new_callable=AsyncMock,
                return_value=fake_cmd,
            ) as mock_update:
                command = await service.propose(
                    _make_proposal(
                        actuator="heater",
                        action="on",
                        duration_seconds=600,
                    )
                )

        # Should stay proposed but with validation errors
        assert command.status == "proposed"
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        # Check the status argument (positional)
        assert call_args[0][1] == "proposed"
        # validation_errors is passed as a keyword arg
        assert call_args.kwargs.get("validation_errors") is not None
        assert "errors" in call_args.kwargs["validation_errors"]


class TestApprove:
    """Tests for CommandService.approve."""

    @pytest.mark.asyncio
    async def test_approve_validated_command(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        fake_cmd = _make_command_log(status="validated")
        session.get = AsyncMock(return_value=fake_cmd)

        with patch.object(
            service.repo,
            "update_status",
            new_callable=AsyncMock,
            return_value=_make_command_log(status="approved"),
        ):
            command = await service.approve(fake_cmd.id)

        assert command.status == "approved"

    @pytest.mark.asyncio
    async def test_approve_proposed_command(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        fake_cmd = _make_command_log(status="proposed")
        session.get = AsyncMock(return_value=fake_cmd)

        with patch.object(
            service.repo,
            "update_status",
            new_callable=AsyncMock,
            return_value=_make_command_log(status="approved"),
        ):
            command = await service.approve(fake_cmd.id)

        assert command.status == "approved"

    @pytest.mark.asyncio
    async def test_approve_rejects_when_hot(self) -> None:
        """Approve should reject heater command if temperature is too high."""
        session = _make_mock_session()
        service = CommandService(session)

        fake_cmd = _make_command_log(
            actuator_name="heater", action="on", status="validated"
        )
        session.get = AsyncMock(return_value=fake_cmd)

        with patch.object(
            service.repo,
            "update_status",
            new_callable=AsyncMock,
            return_value=_make_command_log(status="rejected"),
        ) as mock_update:
            command = await service.approve(
                fake_cmd.id,
                current_readings={"temperature": 35.0},
            )

        assert command.status == "rejected"
        mock_update.assert_called_once()
        assert mock_update.call_args[0][1] == "rejected"

    @pytest.mark.asyncio
    async def test_approve_executed_command_raises(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        fake_cmd = _make_command_log(status="executed")
        session.get = AsyncMock(return_value=fake_cmd)

        with pytest.raises(CommandError, match="Cannot approve"):
            await service.approve(fake_cmd.id)

    @pytest.mark.asyncio
    async def test_approve_nonexistent_raises(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        session.get = AsyncMock(return_value=None)

        with pytest.raises(CommandError, match="not found"):
            await service.approve(uuid.uuid4())


class TestCancel:
    """Tests for CommandService.cancel."""

    @pytest.mark.asyncio
    async def test_cancel_proposed_command(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        fake_cmd = _make_command_log(status="proposed")
        session.get = AsyncMock(return_value=fake_cmd)

        with patch.object(
            service.repo,
            "update_status",
            new_callable=AsyncMock,
            return_value=_make_command_log(status="cancelled"),
        ):
            command = await service.cancel(fake_cmd.id)

        assert command.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_approved_command(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        fake_cmd = _make_command_log(status="approved")
        session.get = AsyncMock(return_value=fake_cmd)

        with patch.object(
            service.repo,
            "update_status",
            new_callable=AsyncMock,
            return_value=_make_command_log(status="cancelled"),
        ):
            command = await service.cancel(fake_cmd.id)

        assert command.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_executed_command_raises(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        fake_cmd = _make_command_log(status="executed")
        session.get = AsyncMock(return_value=fake_cmd)

        with pytest.raises(CommandError, match="Invalid transition"):
            await service.cancel(fake_cmd.id)

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_raises(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        session.get = AsyncMock(return_value=None)

        with pytest.raises(CommandError, match="not found"):
            await service.cancel(uuid.uuid4())


class TestExpireCheck:
    """Tests for CommandService.expire_check."""

    @pytest.mark.asyncio
    async def test_expire_stale_proposed_command(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        stale_cmd = _make_command_log(
            status="proposed",
            valid_until=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        fresh_cmd = _make_command_log(
            status="proposed",
            valid_until=datetime.now(timezone.utc) + timedelta(seconds=300),
        )

        with patch.object(
            service.repo, "list", new_callable=AsyncMock
        ) as mock_list:
            # First call for PROPOSED, second for VALIDATED
            mock_list.side_effect = [[stale_cmd, fresh_cmd], []]

            with patch.object(
                service.repo,
                "update_status",
                new_callable=AsyncMock,
                return_value=_make_command_log(status="expired"),
            ) as mock_update:
                expired = await service.expire_check()

        assert len(expired) == 1
        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_expiry_for_fresh_commands(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        fresh_cmd = _make_command_log(
            status="proposed",
            valid_until=datetime.now(timezone.utc) + timedelta(seconds=300),
        )

        with patch.object(
            service.repo, "list", new_callable=AsyncMock
        ) as mock_list:
            mock_list.side_effect = [[fresh_cmd], []]
            expired = await service.expire_check()

        assert len(expired) == 0


class TestExecute:
    """Tests for CommandService.execute."""

    @pytest.mark.asyncio
    async def test_execute_approved_command(self) -> None:
        session = _make_mock_session()
        publisher = MagicMock()
        publisher.publish = AsyncMock(return_value={"topic": "commands", "payload": {}})
        service = CommandService(session, publisher=publisher)

        fake_cmd = _make_command_log(status="approved")
        session.get = AsyncMock(return_value=fake_cmd)

        # Execute transitions: approved -> executing -> executed
        executing_cmd = _make_command_log(status="executing")
        executed_cmd = _make_command_log(status="executed")

        with patch.object(
            service.repo,
            "update_status",
            new_callable=AsyncMock,
            side_effect=[executing_cmd, executed_cmd],
        ):
            command = await service.execute(fake_cmd.id)

        assert command.status == "executed"

    @pytest.mark.asyncio
    async def test_execute_proposed_command_raises(self) -> None:
        session = _make_mock_session()
        service = CommandService(session)

        fake_cmd = _make_command_log(status="proposed")
        session.get = AsyncMock(return_value=fake_cmd)

        with pytest.raises(CommandError, match="Cannot execute"):
            await service.execute(fake_cmd.id)
