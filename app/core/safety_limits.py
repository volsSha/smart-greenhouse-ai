"""Safety limits for actuator control actions.

All control commands are validated against these limits before
being published to MQTT. Limits define maximum durations, power
levels, cooldowns, and conditional restrictions.
"""

SAFETY_LIMITS: dict[str, dict] = {
    "pump": {
        "max_duration_seconds": 60,
        "cooldown_seconds": 300,
    },
    "fan": {
        "max_power": 100,
        "max_duration_seconds": 600,
    },
    "heater": {
        "max_power": 80,
        "max_duration_seconds": 300,
        "forbidden_if_temperature_above": 28,
    },
    "lamp": {
        "max_duration_seconds": 3600,
    },
}

VALID_ACTUATORS: set[str] = set(SAFETY_LIMITS.keys())

VALID_ACTIONS_PER_ACTUATOR: dict[str, set[str]] = {
    "pump": {"on", "off"},
    "fan": {"on", "off", "set_power"},
    "heater": {"on", "off", "set_power"},
    "lamp": {"on", "off"},
}

VALID_METRICS: list[str] = [
    "temperature",
    "air_humidity",
    "co2",
    "light",
    "soil_moisture",
    "fan_power",
    "pump_state",
    "heater_power",
    "lamp_state",
]
