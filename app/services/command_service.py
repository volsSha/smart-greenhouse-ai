"""Command lifecycle service.

Manages the full lifecycle of actuator commands: propose, validate,
approve, cancel, expire, and execute (MQTT publishing is stubbed for
now -- U14 will add the real MQTT execution).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.command import CommandLog
from app.repositories.command_repository import CommandRepository
from app.schemas.commands import CommandPropose
from app.services.command_publisher import CommandPublisher
from app.services.safety_validator import SafetyValidator, ValidationResult
from app.services.simulator.mode_router import ModeRouter

logger = logging.getLogger(__name__)

# Commands auto-expire after this period if not approved.
DEFAULT_TTL_SECONDS = 300


class CommandStatus(StrEnum):
    """Possible states for a command in its lifecycle."""

    PROPOSED = "proposed"
    VALIDATED = "validated"
    APPROVED = "approved"
    EXECUTING = "executing"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


class CommandError(Exception):
    """Raised when a command lifecycle transition is invalid."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


# Valid state transitions for the command state machine.
VALID_TRANSITIONS: dict[str, set[str]] = {
    CommandStatus.PROPOSED: {
        CommandStatus.VALIDATED,
        CommandStatus.APPROVED,
        CommandStatus.REJECTED,
        CommandStatus.CANCELLED,
        CommandStatus.EXPIRED,
    },
    CommandStatus.VALIDATED: {
        CommandStatus.APPROVED,
        CommandStatus.REJECTED,
        CommandStatus.CANCELLED,
        CommandStatus.EXPIRED,
    },
    CommandStatus.APPROVED: {CommandStatus.EXECUTING, CommandStatus.CANCELLED},
    CommandStatus.EXECUTING: {CommandStatus.EXECUTED, CommandStatus.FAILED, CommandStatus.CANCELLED},
    CommandStatus.EXECUTED: set(),
    CommandStatus.CANCELLED: set(),
    CommandStatus.REJECTED: set(),
    CommandStatus.EXPIRED: set(),
    CommandStatus.FAILED: set(),
}


def _check_transition(current: str, target: str) -> None:
    """Raise CommandError if the transition is not allowed."""
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise CommandError(
            f"Invalid transition from '{current}' to '{target}'. "
            f"Allowed: {sorted(allowed) if allowed else ['(terminal)']}"
        )


class CommandService:
    """Service for managing command lifecycle."""

    def __init__(
        self,
        session: AsyncSession,
        publisher: CommandPublisher | None = None,
    ) -> None:
        self.session = session
        self.repo = CommandRepository(session)
        self.validator = SafetyValidator()
        self.publisher = publisher

    async def propose(
        self,
        data: CommandPropose,
        current_readings: dict | None = None,
        recent_commands: list | None = None,
    ) -> CommandLog:
        """Propose a new command and run safety validation.

        Creates a CommandLog with PROPOSED status, validates it, and
        transitions to VALIDATED if safe or keeps PROPOSED with errors
        if unsafe.

        Returns the created CommandLog.
        """
        # Create the command with PROPOSED status
        valid_until = datetime.now(timezone.utc) + timedelta(
            seconds=DEFAULT_TTL_SECONDS
        )

        command = await self.repo.create(
            group_id=data.group_id,
            greenhouse_id=data.greenhouse_id,
            zone_id=data.zone_id,
            actuator_name=data.actuator,
            action=data.action,
            value=data.value,
            duration_seconds=data.duration_seconds,
            source=data.source,
            reason=data.reason,
            status=CommandStatus.PROPOSED,
            valid_until=valid_until,
            mode=data.mode,
        )

        # Run safety validation
        result: ValidationResult = self.validator.validate_command(
            data,
            current_readings=current_readings,
            recent_commands=recent_commands,
        )

        if result.is_valid:
            _check_transition(CommandStatus.PROPOSED, CommandStatus.VALIDATED)
            command = await self.repo.update_status(
                command.id,
                CommandStatus.VALIDATED,
            )
            logger.info(
                "Command %s proposed and validated: %s %s",
                command.id,
                data.actuator,
                data.action,
            )
        else:
            logger.warning(
                "Command %s proposed but failed validation: %s",
                command.id,
                result.errors,
            )
            # Keep status as PROPOSED but store errors
            command = await self.repo.update_status(
                command.id,
                CommandStatus.PROPOSED,
                validation_errors={"errors": result.errors, "warnings": result.warnings},
            )

        return command

    async def approve(
        self,
        command_id: uuid.UUID,
        current_readings: dict | None = None,
        recent_commands: list | None = None,
        execute: bool = False,
        mode_router: ModeRouter | None = None,
    ) -> CommandLog:
        """Approve a proposed or validated command.

        Re-validates the command at approval time. If validation passes,
        transitions to APPROVED. If it fails, transitions to REJECTED.

        Raises CommandError if the command is not found or in a terminal state.
        """
        command = await self.repo.get_by_id(command_id)
        if command is None:
            raise CommandError(f"Command {command_id} not found")

        if command.status not in (CommandStatus.PROPOSED, CommandStatus.VALIDATED):
            raise CommandError(
                f"Cannot approve command in '{command.status}' state"
            )

        # Re-validate at approval time
        result = self.validator.revalidate_at_approval(
            actuator=command.actuator_name,
            action=command.action,
            value=command.value,
            duration_seconds=command.duration_seconds,
            current_readings=current_readings,
            recent_commands=recent_commands,
        )

        if result.is_valid:
            _check_transition(command.status, CommandStatus.APPROVED)
            command = await self.repo.update_status(
                command.id,
                CommandStatus.APPROVED,
            )
            logger.info("Command %s approved", command.id)
            if execute:
                command = await self.execute(command.id, command=command, mode_router=mode_router)
        else:
            _check_transition(command.status, CommandStatus.REJECTED)
            command = await self.repo.update_status(
                command.id,
                CommandStatus.REJECTED,
                validation_errors={"errors": result.errors, "warnings": result.warnings},
            )
            logger.warning(
                "Command %s rejected at approval: %s",
                command.id,
                result.errors,
            )

        return command

    async def cancel(self, command_id: uuid.UUID) -> CommandLog:
        """Cancel a command that is in a cancellable state.

        Raises CommandError if the command is not found or not cancellable.
        """
        command = await self.repo.get_by_id(command_id)
        if command is None:
            raise CommandError(f"Command {command_id} not found")

        _check_transition(command.status, CommandStatus.CANCELLED)
        command = await self.repo.update_status(command.id, CommandStatus.CANCELLED)
        logger.info("Command %s cancelled", command.id)
        return command

    async def expire_check(self) -> list[CommandLog]:
        """Find and mark expired commands.

        Commands with valid_until < now that are still in PROPOSED or
        VALIDATED state are transitioned to EXPIRED.

        Returns list of expired commands.
        """
        now = datetime.now(timezone.utc)
        expired_commands = await self.repo.list(
            status=CommandStatus.PROPOSED,
        )
        # Also check VALIDATED
        validated = await self.repo.list(status=CommandStatus.VALIDATED)
        expired_commands.extend(validated)

        expired: list[CommandLog] = []
        for cmd in expired_commands:
            if cmd.valid_until is not None and cmd.valid_until < now:
                _check_transition(cmd.status, CommandStatus.EXPIRED)
                cmd = await self.repo.update_status(cmd.id, CommandStatus.EXPIRED)
                expired.append(cmd)
                logger.info("Command %s expired", cmd.id)

        return expired

    async def execute(
        self,
        command_id: uuid.UUID,
        command: CommandLog | None = None,
        mode_router: ModeRouter | None = None,
    ) -> CommandLog:
        """Execute an approved command."""
        command = command or await self.repo.get_by_id(command_id)
        if command is None:
            raise CommandError(f"Command {command_id} not found")

        if command.status == CommandStatus.EXECUTED:
            return command
        if command.status != CommandStatus.APPROVED:
            raise CommandError(
                f"Cannot execute command in '{command.status}' state"
            )

        _check_transition(command.status, CommandStatus.EXECUTING)
        command = await self.repo.update_status(command.id, CommandStatus.EXECUTING)
        mode = getattr(command, "mode", "mqtt")
        logger.info("Command %s executing (mode=%s)", command.id, mode)

        # Route based on mode
        if mode == "simulator":
            try:
                if mode_router is None:
                    raise CommandError("Mode router not configured for simulator execution")
                publish_result = await mode_router.route(command, self.session)
            except Exception as exc:
                _check_transition(command.status, CommandStatus.FAILED)
                failed = await self.repo.update_status(
                    command.id,
                    CommandStatus.FAILED,
                    validation_errors={"errors": [f"Simulator execution failed: {exc}"]},
                )
                logger.warning("Command %s failed in simulator mode", command.id, exc_info=True)
                return failed
        else:
            # MQTT mode (default)
            if self.publisher is None:
                raise CommandError("Command publisher is not configured")

            try:
                publish_result = await self.publisher.publish(command)
            except Exception as exc:
                _check_transition(command.status, CommandStatus.FAILED)
                failed = await self.repo.update_status(
                    command.id,
                    CommandStatus.FAILED,
                    validation_errors={"errors": [f"MQTT publish failed: {exc}"]},
                )
                logger.warning("Command %s failed during MQTT publish", command.id, exc_info=True)
                return failed

        _check_transition(command.status, CommandStatus.EXECUTED)
        command = await self.repo.update_status(
            command.id,
            CommandStatus.EXECUTED,
            validation_errors={"publish": publish_result} if mode != "simulator" else None,
        )
        logger.info("Command %s executed (mode=%s)", command.id, mode)
        return command

    async def get_recent(
        self,
        group_id: uuid.UUID,
        greenhouse_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[CommandLog]:
        """Get recent commands for a group, optionally filtered."""
        return await self.repo.get_recent(
            group_id=group_id,
            greenhouse_id=greenhouse_id,
            zone_id=zone_id,
            limit=limit,
        )

    async def get_by_id(self, command_id: uuid.UUID) -> CommandLog | None:
        """Get a command by ID."""
        return await self.repo.get_by_id(command_id)
