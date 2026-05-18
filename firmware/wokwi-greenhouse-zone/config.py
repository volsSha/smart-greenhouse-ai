"""Editable Wokwi MicroPython MQTT settings.

For hosted Wokwi, use a public MQTT broker such as Mosquitto on a VPS,
then paste the broker host, port, and demo credentials below. Keep secrets out of git.
"""

WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""

# Replace these with the public MQTT broker endpoint.
MQTT_HOST = "mqtt.example.com"
MQTT_PORT = 8883
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
