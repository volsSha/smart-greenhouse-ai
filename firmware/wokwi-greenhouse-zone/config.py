"""Editable Wokwi MicroPython MQTT settings.

For hosted Wokwi, expose the local Docker Mosquitto port with an ngrok TCP
tunnel, then paste the generated host and port below. Keep secrets out of git.
"""

WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""

# Replace these with the host and port from `ngrok tcp 11883`.
MQTT_HOST = "0.tcp.ngrok.io"
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASSWORD = ""
MQTT_KEEPALIVE_SECONDS = 60

GROUP_ID = "group-001"
GREENHOUSE_ID = "gh-001"
ZONE_ID = "zone-01"
DEVICE_ID = "wokwi-zone-01"

PUBLISH_INTERVAL_SECONDS = 5
MQTT_QOS = 0

TELEMETRY_TOPIC_TEMPLATE = (
    "greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/telemetry"
)
COMMAND_TOPIC_TEMPLATE = (
    "greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/commands"
)

DHT_PIN = 15
SOIL_PIN = 34
LIGHT_PIN = 35
CO2_PIN = 32
PUMP_LED_PIN = 25
FAN_LED_PIN = 26
HEATER_LED_PIN = 27
LAMP_LED_PIN = 14
