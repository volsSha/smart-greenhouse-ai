"""Tests for MQTT-mode command publishing."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import MQTTSettings
from app.services.command_publisher import CommandPublisher
from app.services.command_service import CommandService, CommandStatus


def _command(mode: str = "mqtt") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        group_id=uuid.uuid4(),
        greenhouse_id=uuid.uuid4(),
        zone_id=uuid.uuid4(),
        actuator_id=None,
        actuator_name="pump",
        action="on",
        value=50.0,
        unit=None,
        duration_seconds=30,
        source="ai_agent",
        reason="needs water",
        validation_errors=None,
        status="approved",
        mode=mode,
        valid_until=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestCommandPublisher:
    @pytest.mark.asyncio
    async def test_publish_uses_qos_1_and_expected_payload(self) -> None:
        client = MagicMock()
        client.connect = AsyncMock()
        client.publish = AsyncMock()
        client.disconnect = AsyncMock()
        publisher = CommandPublisher(MQTTSettings(), client=client)
        command = _command(mode="mqtt")

        result = await publisher.publish(command)

        client.connect.assert_awaited_once()
        client.publish.assert_awaited_once()
        topic, payload = client.publish.call_args.args[:2]
        assert topic.endswith("/commands")
        assert client.publish.call_args.kwargs["qos"] == 1
        assert str(command.id) in payload
        assert '"actuator":"pump"' in payload
        assert '"action":"on"' in payload
        assert result["payload"]["command_id"] == str(command.id)
        client.disconnect.assert_awaited_once()


class TestCommandServiceSimulatorMode:
    @pytest.mark.asyncio
    async def test_execute_simulator_mode_routes_and_marks_executed(self) -> None:
        session = MagicMock()
        command = _command(mode="simulator")
        executing_command = _command(mode="simulator")
        executing_command.status = CommandStatus.EXECUTING
        executed_command = _command(mode="simulator")
        executed_command.status = CommandStatus.EXECUTED
        mode_router = MagicMock()
        mode_router.route = AsyncMock(return_value={"applied": True})
        publisher = MagicMock()
        publisher.publish = AsyncMock()
        service = CommandService(session, publisher=publisher)

        with patch.object(
            service.repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=command,
        ), patch.object(
            service.repo,
            "update_status",
            new_callable=AsyncMock,
            side_effect=[executing_command, executed_command],
        ) as update_status:
            result = await service.execute(command.id, mode_router=mode_router)

        assert result.status == CommandStatus.EXECUTED
        mode_router.route.assert_awaited_once_with(executing_command, session)
        publisher.publish.assert_not_awaited()
        assert update_status.await_args_list[1].kwargs["validation_errors"] is None

    @pytest.mark.asyncio
    async def test_execute_simulator_mode_without_router_marks_failed(self) -> None:
        session = MagicMock()
        command = _command(mode="simulator")
        executing_command = _command(mode="simulator")
        executing_command.status = CommandStatus.EXECUTING
        failed_command = _command(mode="simulator")
        failed_command.status = CommandStatus.FAILED
        service = CommandService(session, publisher=MagicMock())

        with patch.object(
            service.repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=command,
        ), patch.object(
            service.repo,
            "update_status",
            new_callable=AsyncMock,
            side_effect=[executing_command, failed_command],
        ) as update_status:
            result = await service.execute(command.id)

        assert result.status == CommandStatus.FAILED
        assert "Simulator execution failed" in update_status.await_args_list[1].kwargs["validation_errors"]["errors"][0]

    @pytest.mark.asyncio
    async def test_execute_simulator_mode_router_error_marks_failed(self) -> None:
        session = MagicMock()
        command = _command(mode="simulator")
        executing_command = _command(mode="simulator")
        executing_command.status = CommandStatus.EXECUTING
        failed_command = _command(mode="simulator")
        failed_command.status = CommandStatus.FAILED
        mode_router = MagicMock()
        mode_router.route = AsyncMock(side_effect=RuntimeError("unknown zone"))
        service = CommandService(session, publisher=MagicMock())

        with patch.object(
            service.repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=command,
        ), patch.object(
            service.repo,
            "update_status",
            new_callable=AsyncMock,
            side_effect=[executing_command, failed_command],
        ) as update_status:
            result = await service.execute(command.id, mode_router=mode_router)

        assert result.status == CommandStatus.FAILED
        assert "unknown zone" in update_status.await_args_list[1].kwargs["validation_errors"]["errors"][0]


class TestCommandServiceMqttMode:
    @pytest.mark.asyncio
    async def test_execute_mqtt_mode_publishes_once_and_marks_executed(self) -> None:
        session = MagicMock()
        command = _command(mode="mqtt")
        repo_command = _command(mode="mqtt")
        repo_command.status = CommandStatus.EXECUTING
        executed_command = _command(mode="mqtt")
        executed_command.status = CommandStatus.EXECUTED

        publisher = MagicMock()
        publisher.publish = AsyncMock(return_value={"topic": "commands", "payload": {}})
        service = CommandService(session, publisher=publisher)

        with patch.object(
            service.repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=command,
        ), patch.object(
            service.repo,
            "update_status",
            new_callable=AsyncMock,
            side_effect=[repo_command, executed_command],
        ) as update_status:
            result = await service.execute(command.id)

        assert result.status == CommandStatus.EXECUTED
        publisher.publish.assert_awaited_once_with(repo_command)
        assert update_status.await_args_list[0].args[1] == CommandStatus.EXECUTING
        assert update_status.await_args_list[1].args[1] == CommandStatus.EXECUTED

    @pytest.mark.asyncio
    async def test_execute_mqtt_publish_failure_marks_failed(self) -> None:
        session = MagicMock()
        command = _command(mode="mqtt")
        executing_command = _command(mode="mqtt")
        executing_command.status = CommandStatus.EXECUTING
        failed_command = _command(mode="mqtt")
        failed_command.status = CommandStatus.FAILED

        publisher = MagicMock()
        publisher.publish = AsyncMock(side_effect=RuntimeError("broker down"))
        service = CommandService(session, publisher=publisher)

        with patch.object(
            service.repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=command,
        ), patch.object(
            service.repo,
            "update_status",
            new_callable=AsyncMock,
            side_effect=[executing_command, failed_command],
        ):
            result = await service.execute(command.id)

        assert result.status == CommandStatus.FAILED
