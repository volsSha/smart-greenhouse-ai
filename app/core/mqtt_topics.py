"""MQTT topic builder functions using the readable topic hierarchy.

Canonical form:
    greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/{channel}

Where channel is one of: telemetry, commands, alerts, state.
"""


def telemetry_topic(group_id: str, greenhouse_id: str, zone_id: str) -> str:
    """Build the MQTT telemetry topic for a specific zone."""
    return (
        f"greenhouse-groups/{group_id}"
        f"/greenhouses/{greenhouse_id}"
        f"/zones/{zone_id}/telemetry"
    )


def command_topic(group_id: str, greenhouse_id: str, zone_id: str) -> str:
    """Build the MQTT command topic for a specific zone."""
    return (
        f"greenhouse-groups/{group_id}"
        f"/greenhouses/{greenhouse_id}"
        f"/zones/{zone_id}/commands"
    )


def alert_topic(group_id: str, greenhouse_id: str, zone_id: str) -> str:
    """Build the MQTT alert topic for a specific zone."""
    return (
        f"greenhouse-groups/{group_id}"
        f"/greenhouses/{greenhouse_id}"
        f"/zones/{zone_id}/alerts"
    )


def state_topic(group_id: str, greenhouse_id: str, zone_id: str) -> str:
    """Build the MQTT state topic for a specific zone."""
    return (
        f"greenhouse-groups/{group_id}"
        f"/greenhouses/{greenhouse_id}"
        f"/zones/{zone_id}/state"
    )


def group_topic(group_id: str) -> str:
    """Build a wildcard subscription topic for all zones in a group."""
    return f"greenhouse-groups/{group_id}/#"


def all_telemetry_topic() -> str:
    """Build a wildcard subscription topic for all telemetry across all groups.

    Returns six-segment pattern matching the canonical topic hierarchy:
        greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/telemetry
    """
    return "greenhouse-groups/+/greenhouses/+/zones/+/telemetry"
