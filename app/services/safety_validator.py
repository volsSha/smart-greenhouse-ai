"""Deterministic safety validation for actuator commands.

All control commands are validated against SAFETY_LIMITS before approval.
The validator checks actuator existence, action validity, duration limits,
power limits, cooldown periods, conditional restrictions, and mutually
unsafe combinations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.safety_limits import (
    SAFETY_LIMITS,
    VALID_ACTUATORS,
    VALID_ACTIONS_PER_ACTUATOR,
)
from app.schemas.commands import CommandPropose

# Mutually unsafe actuator combinations that cannot run simultaneously
# in the same zone.
MUTUALLY_UNSAFE_PAIRS: list[tuple[str, str]] = [
    ("heater", "fan"),
]


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating a command proposal."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class SafetyValidator:
    """Deterministic safety validator for actuator commands.

    All validation methods are pure functions that return a ValidationResult.
    No I/O or side effects.
    """

    def validate_command(
        self,
        proposal: CommandPropose,
        current_readings: dict | None = None,
        recent_commands: list | None = None,
    ) -> ValidationResult:
        """Validate a command proposal against all safety rules.

        Args:
            proposal: The command proposal to validate.
            current_readings: Optional dict of current sensor readings
                (e.g. {"temperature": 25.0, "humidity": 60.0}).
            recent_commands: Optional list of recent command dicts from the
                same zone, used for cooldown checks. Each dict should have
                keys: actuator_name, created_at.

        Returns:
            ValidationResult with is_valid, errors, and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Actuator must be in VALID_ACTUATORS
        if proposal.actuator not in VALID_ACTUATORS:
            errors.append(
                f"Unknown actuator '{proposal.actuator}'. "
                f"Valid actuators: {sorted(VALID_ACTUATORS)}"
            )

        # 2. Action must be valid for the actuator
        valid_actions = VALID_ACTIONS_PER_ACTUATOR.get(proposal.actuator, set())
        if proposal.action not in valid_actions:
            errors.append(
                f"Invalid action '{proposal.action}' for actuator '{proposal.actuator}'. "
                f"Valid actions: {sorted(valid_actions)}"
            )

        # 3. Duration must not exceed max_duration_seconds
        limits = SAFETY_LIMITS.get(proposal.actuator, {})
        max_duration = limits.get("max_duration_seconds")
        if max_duration is not None and proposal.duration_seconds is not None:
            if proposal.duration_seconds > max_duration:
                errors.append(
                    f"Duration {proposal.duration_seconds}s exceeds maximum "
                    f"{max_duration}s for actuator '{proposal.actuator}'"
                )

        # 4. Power must not exceed max_power
        max_power = limits.get("max_power")
        if max_power is not None and proposal.value is not None:
            if proposal.value > max_power:
                errors.append(
                    f"Power value {proposal.value} exceeds maximum "
                    f"{max_power} for actuator '{proposal.actuator}'"
                )

        # 5. Heater: forbidden if temperature above threshold
        forbidden_temp = limits.get("forbidden_if_temperature_above")
        if forbidden_temp is not None and current_readings:
            current_temp = current_readings.get("temperature")
            if current_temp is not None and current_temp > forbidden_temp:
                if proposal.actuator == "heater" and proposal.action in ("on", "set_power"):
                    errors.append(
                        f"Cannot activate heater when temperature is "
                        f"{current_temp}C (forbidden above {forbidden_temp}C)"
                    )

        # 6. Cooldown: no same-zone same-actuator command within cooldown_seconds
        cooldown_seconds = limits.get("cooldown_seconds")
        if (
            cooldown_seconds is not None
            and recent_commands
            and proposal.action != "off"
        ):
            now = datetime.now(timezone.utc)
            for cmd in recent_commands:
                cmd_actuator = getattr(cmd, "actuator_name", None) or cmd.get("actuator_name")
                if cmd_actuator == proposal.actuator:
                    cmd_time = getattr(cmd, "created_at", None) or cmd.get("created_at")
                    if cmd_time is not None:
                        if isinstance(cmd_time, datetime):
                            elapsed = (now - cmd_time).total_seconds()
                        else:
                            continue
                        if elapsed < cooldown_seconds:
                            errors.append(
                                f"Cooldown active for '{proposal.actuator}' in this zone. "
                                f"Elapsed {elapsed:.0f}s, required {cooldown_seconds}s"
                            )
                            break  # Only report once

        # 7. Mutually unsafe combinations
        if proposal.action in ("on", "set_power") and recent_commands:
            now = datetime.now(timezone.utc)
            for unsafe_pair in MUTUALLY_UNSAFE_PAIRS:
                other_actuator = None
                if proposal.actuator == unsafe_pair[0]:
                    other_actuator = unsafe_pair[1]
                elif proposal.actuator == unsafe_pair[1]:
                    other_actuator = unsafe_pair[0]

                if other_actuator is None:
                    continue

                for cmd in recent_commands:
                    cmd_actuator = getattr(cmd, "actuator_name", None) or cmd.get("actuator_name")
                    cmd_action = getattr(cmd, "action", None) or cmd.get("action")
                    cmd_status = getattr(cmd, "status", None) or cmd.get("status")
                    if cmd_actuator == other_actuator and cmd_action in ("on", "set_power"):
                        # Only consider active commands
                        if cmd_status in ("approved", "executing", "executed", "validated"):
                            errors.append(
                                f"Mutually unsafe: cannot activate '{proposal.actuator}' "
                                f"when '{other_actuator}' is active in the same zone"
                            )
                            break
                else:
                    continue
                break  # Break outer loop if inner broke

        # Warnings (non-blocking)
        if proposal.duration_seconds is None and proposal.action in ("on", "set_power"):
            warnings.append(
                "No duration specified for actuator activation. "
                "Consider setting duration_seconds."
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def revalidate_at_approval(
        self,
        actuator: str,
        action: str,
        value: float | None,
        duration_seconds: int | None,
        current_readings: dict | None = None,
        recent_commands: list | None = None,
    ) -> ValidationResult:
        """Re-validate a command at approval time.

        This is a convenience wrapper that constructs a temporary proposal
        and calls validate_command. Used by CommandService.approve() to
        re-check conditions that may have changed since proposal time.

        Args:
            actuator: Actuator type name.
            action: Action to perform.
            value: Numeric value (e.g. power level).
            duration_seconds: How long to run.
            current_readings: Current sensor readings dict.
            recent_commands: Recent commands for cooldown/conflict checks.

        Returns:
            ValidationResult from re-validation.
        """
        # Build a minimal proposal with the needed fields.
        # We use a dummy UUID for the IDs since they are not relevant
        # to safety validation.
        from uuid import uuid4

        proposal = CommandPropose(
            group_id=uuid4(),
            greenhouse_id=uuid4(),
            zone_id=uuid4(),
            actuator=actuator,
            action=action,
            value=value,
            duration_seconds=duration_seconds,
        )
        return self.validate_command(
            proposal,
            current_readings=current_readings,
            recent_commands=recent_commands,
        )
