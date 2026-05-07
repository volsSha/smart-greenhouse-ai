"""Unit tests for the safety validator.

Tests cover:
- Valid pump command passes validation
- Reject over-duration commands
- Reject heater activation when temperature is too high
- Reject commands during cooldown period
- Reject mutually unsafe actuator combinations
- Reject unknown actuators and invalid actions
- Reject power values exceeding maximum
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.schemas.commands import CommandPropose
from app.services.safety_validator import SafetyValidator


def _make_proposal(
    actuator: str = "pump",
    action: str = "on",
    value: float | None = None,
    duration_seconds: int | None = 30,
    zone_id: uuid.UUID | None = None,
) -> CommandPropose:
    """Create a CommandPropose with sensible defaults."""
    return CommandPropose(
        group_id=uuid.uuid4(),
        greenhouse_id=uuid.uuid4(),
        zone_id=zone_id or uuid.uuid4(),
        actuator=actuator,
        action=action,
        value=value,
        duration_seconds=duration_seconds,
        source="manual",
    )


class TestSafePumpCommand:
    """A valid pump 'on' command with reasonable duration should pass."""

    def test_valid_pump_on(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="pump", action="on", duration_seconds=30)
        result = validator.validate_command(proposal)
        assert result.is_valid is True
        assert result.errors == []

    def test_valid_pump_off(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="pump", action="off")
        result = validator.validate_command(proposal)
        assert result.is_valid is True

    def test_valid_fan_set_power(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(
            actuator="fan", action="set_power", value=50, duration_seconds=300
        )
        result = validator.validate_command(proposal)
        assert result.is_valid is True

    def test_valid_lamp_on(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="lamp", action="on", duration_seconds=1800)
        result = validator.validate_command(proposal)
        assert result.is_valid is True


class TestRejectOverDuration:
    """Commands exceeding max_duration_seconds should be rejected."""

    def test_pump_over_duration(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="pump", duration_seconds=120)
        result = validator.validate_command(proposal)
        assert result.is_valid is False
        assert any("exceeds maximum" in e for e in result.errors)

    def test_heater_over_duration(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="heater", action="on", duration_seconds=600)
        result = validator.validate_command(proposal)
        assert result.is_valid is False
        assert any("exceeds maximum" in e for e in result.errors)

    def test_fan_over_duration(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="fan", action="on", duration_seconds=900)
        result = validator.validate_command(proposal)
        assert result.is_valid is False
        assert any("exceeds maximum" in e for e in result.errors)


class TestRejectOverPower:
    """Commands exceeding max_power should be rejected."""

    def test_heater_over_power(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(
            actuator="heater", action="set_power", value=100, duration_seconds=60
        )
        result = validator.validate_command(proposal)
        assert result.is_valid is False
        assert any("exceeds maximum" in e for e in result.errors)

    def test_fan_over_power(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(
            actuator="fan", action="set_power", value=150, duration_seconds=60
        )
        result = validator.validate_command(proposal)
        assert result.is_valid is False
        assert any("exceeds maximum" in e for e in result.errors)


class TestRejectHeaterWhenHot:
    """Heater activation should be rejected when temperature is too high."""

    def test_heater_on_above_threshold(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="heater", action="on")
        result = validator.validate_command(
            proposal, current_readings={"temperature": 30.0}
        )
        assert result.is_valid is False
        assert any("forbidden" in e.lower() for e in result.errors)

    def test_heater_on_at_threshold(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="heater", action="on")
        # Temperature exactly at threshold should be allowed (forbidden > 28, not >=)
        result = validator.validate_command(
            proposal, current_readings={"temperature": 28.0}
        )
        assert result.is_valid is True

    def test_heater_on_below_threshold(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="heater", action="on")
        result = validator.validate_command(
            proposal, current_readings={"temperature": 20.0}
        )
        assert result.is_valid is True

    def test_heater_off_allowed_when_hot(self) -> None:
        """Turning heater OFF should always be allowed."""
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="heater", action="off")
        result = validator.validate_command(
            proposal, current_readings={"temperature": 35.0}
        )
        assert result.is_valid is True


class TestRejectDuringCooldown:
    """Same-zone same-actuator commands should be rejected during cooldown."""

    def test_pump_cooldown(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="pump", action="on", duration_seconds=30)

        now = datetime.now(timezone.utc)
        recent = [
            SimpleNamespace(
                actuator_name="pump",
                created_at=now - timedelta(seconds=60),
            )
        ]
        result = validator.validate_command(proposal, recent_commands=recent)
        assert result.is_valid is False
        assert any("Cooldown" in e for e in result.errors)

    def test_pump_cooldown_expired(self) -> None:
        """Command should pass after cooldown period elapses."""
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="pump", action="on", duration_seconds=30)

        now = datetime.now(timezone.utc)
        recent = [
            SimpleNamespace(
                actuator_name="pump",
                created_at=now - timedelta(seconds=301),
            )
        ]
        result = validator.validate_command(proposal, recent_commands=recent)
        assert result.is_valid is True

    def test_off_bypasses_cooldown(self) -> None:
        """Turning an actuator OFF should bypass cooldown checks."""
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="pump", action="off")

        now = datetime.now(timezone.utc)
        recent = [
            SimpleNamespace(
                actuator_name="pump",
                created_at=now - timedelta(seconds=10),
            )
        ]
        result = validator.validate_command(proposal, recent_commands=recent)
        assert result.is_valid is True

    def test_different_actuator_no_cooldown(self) -> None:
        """Different actuator should not trigger cooldown."""
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="lamp", action="on", duration_seconds=60)

        now = datetime.now(timezone.utc)
        recent = [
            SimpleNamespace(
                actuator_name="pump",
                created_at=now - timedelta(seconds=10),
            )
        ]
        result = validator.validate_command(proposal, recent_commands=recent)
        assert result.is_valid is True


class TestMutuallyUnsafeCombinations:
    """Heater and fan cannot both be active in the same zone."""

    def test_heater_rejected_when_fan_active(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="heater", action="on", duration_seconds=60)

        recent = [
            SimpleNamespace(
                actuator_name="fan",
                action="on",
                status="approved",
                created_at=datetime.now(timezone.utc),
            )
        ]
        result = validator.validate_command(proposal, recent_commands=recent)
        assert result.is_valid is False
        assert any("Mutually unsafe" in e for e in result.errors)

    def test_fan_rejected_when_heater_active(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="fan", action="on", duration_seconds=60)

        recent = [
            SimpleNamespace(
                actuator_name="heater",
                action="on",
                status="executed",
                created_at=datetime.now(timezone.utc),
            )
        ]
        result = validator.validate_command(proposal, recent_commands=recent)
        assert result.is_valid is False
        assert any("Mutually unsafe" in e for e in result.errors)

    def test_heater_allowed_when_fan_off(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="heater", action="on", duration_seconds=60)

        recent = [
            SimpleNamespace(
                actuator_name="fan",
                action="off",
                status="executed",
                created_at=datetime.now(timezone.utc),
            )
        ]
        result = validator.validate_command(proposal, recent_commands=recent)
        assert result.is_valid is True


class TestUnknownActuatorAndAction:
    """Unknown actuators and invalid actions should be rejected."""

    def test_unknown_actuator(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="sprinkler", action="on")
        result = validator.validate_command(proposal)
        assert result.is_valid is False
        assert any("Unknown actuator" in e for e in result.errors)

    def test_invalid_action(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="pump", action="explode")
        result = validator.validate_command(proposal)
        assert result.is_valid is False
        assert any("Invalid action" in e for e in result.errors)

    def test_set_power_for_pump_rejected(self) -> None:
        """Pump only supports on/off, not set_power."""
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="pump", action="set_power", value=50)
        result = validator.validate_command(proposal)
        assert result.is_valid is False
        assert any("Invalid action" in e for e in result.errors)


class TestWarnings:
    """Non-blocking warnings should be generated for certain conditions."""

    def test_no_duration_warning(self) -> None:
        validator = SafetyValidator()
        proposal = _make_proposal(actuator="pump", action="on", duration_seconds=None)
        result = validator.validate_command(proposal)
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("No duration" in w for w in result.warnings)


class TestRevalidateAtApproval:
    """The revalidate_at_approval convenience method should work correctly."""

    def test_revalidate_valid(self) -> None:
        validator = SafetyValidator()
        result = validator.revalidate_at_approval(
            actuator="pump",
            action="on",
            value=None,
            duration_seconds=30,
        )
        assert result.is_valid is True

    def test_revalidate_invalid(self) -> None:
        validator = SafetyValidator()
        result = validator.revalidate_at_approval(
            actuator="heater",
            action="on",
            value=None,
            duration_seconds=600,
        )
        assert result.is_valid is False
