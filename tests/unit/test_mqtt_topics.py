"""Tests for app.core.mqtt_topics — topic builder functions."""

import re

from app.core.mqtt_topics import (
    all_telemetry_topic,
    alert_topic,
    command_topic,
    group_topic,
    state_topic,
    telemetry_topic,
)


class TestTelemetryTopic:
    """Tests for telemetry_topic builder."""

    def test_returns_correct_readable_form(self) -> None:
        topic = telemetry_topic("group-001", "gh-001", "zone-01")
        assert (
            topic
            == "greenhouse-groups/group-001/greenhouses/gh-001/zones/zone-01/telemetry"
        )

    def test_different_ids(self) -> None:
        topic = telemetry_topic("group-002", "gh-003", "zone-05")
        assert (
            topic
            == "greenhouse-groups/group-002/greenhouses/gh-003/zones/zone-05/telemetry"
        )


class TestCommandTopic:
    """Tests for command_topic builder."""

    def test_returns_correct_readable_form(self) -> None:
        topic = command_topic("group-001", "gh-002", "zone-02")
        assert (
            topic
            == "greenhouse-groups/group-001/greenhouses/gh-002/zones/zone-02/commands"
        )


class TestAlertTopic:
    """Tests for alert_topic builder."""

    def test_returns_correct_readable_form(self) -> None:
        topic = alert_topic("group-001", "gh-001", "zone-01")
        assert (
            topic
            == "greenhouse-groups/group-001/greenhouses/gh-001/zones/zone-01/alerts"
        )


class TestStateTopic:
    """Tests for state_topic builder."""

    def test_returns_correct_readable_form(self) -> None:
        topic = state_topic("group-001", "gh-001", "zone-01")
        assert (
            topic
            == "greenhouse-groups/group-001/greenhouses/gh-001/zones/zone-01/state"
        )


class TestGroupTopic:
    """Tests for group_topic wildcard subscription builder."""

    def test_returns_group_wildcard(self) -> None:
        topic = group_topic("group-001")
        assert topic == "greenhouse-groups/group-001/#"


class TestAllTelemetryTopic:
    """Tests for all_telemetry_topic wildcard subscription builder."""

    def test_returns_full_wildcard_telemetry(self) -> None:
        topic = all_telemetry_topic()
        assert topic == "greenhouse-groups/+/greenhouses/+/zones/+/telemetry"

    def test_wildcard_shape_matches_specific_telemetry_topics(self) -> None:
        topic = telemetry_topic("group-001", "gh-001", "zone-01")
        pattern = all_telemetry_topic()
        assert len(topic.split("/")) == len(pattern.split("/"))
        assert pattern.split("/") == [
            "greenhouse-groups",
            "+",
            "greenhouses",
            "+",
            "zones",
            "+",
            "telemetry",
        ]

    def test_wildcard_matches_micropython_constructed_telemetry_topic(self) -> None:
        micropython_topic = (
            "greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}"
            "/zones/{zone_id}/telemetry"
        ).format(
            group_id="group-001",
            greenhouse_id="gh-001",
            zone_id="zone-01",
        )
        wildcard_regex = re.escape(all_telemetry_topic()).replace("\\+", "[^/]+")

        assert micropython_topic == telemetry_topic("group-001", "gh-001", "zone-01")
        assert re.fullmatch(wildcard_regex, micropython_topic)


class TestTopicConsistency:
    """Verify topic patterns match the documented examples from ARCHITECTURE.md."""

    def test_documented_example_telemetry(self) -> None:
        """Matches the exact example from ROUTES.md."""
        topic = telemetry_topic("group-001", "gh-001", "zone-01")
        expected = "greenhouse-groups/group-001/greenhouses/gh-001/zones/zone-01/telemetry"
        assert topic == expected

    def test_documented_example_command(self) -> None:
        """Matches the command example from ROUTES.md."""
        topic = command_topic("group-001", "gh-002", "zone-02")
        expected = "greenhouse-groups/group-001/greenhouses/gh-002/zones/zone-02/commands"
        assert topic == expected
