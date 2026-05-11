"""Wokwi ESP32 MicroPython firmware for one greenhouse zone.

Publishes telemetry envelopes matching app/schemas/telemetry.py and consumes
commands published by app/services/command_publisher.py.
"""

import json
import time

import config
import dht
import network
from machine import ADC, Pin
from umqtt.simple import MQTTClient

try:
    import ntptime
except ImportError:  # pragma: no cover - MicroPython runtime dependent
    ntptime = None

TELEMETRY_TOPIC = config.TELEMETRY_TOPIC_TEMPLATE.format(
    group_id=config.GROUP_ID,
    greenhouse_id=config.GREENHOUSE_ID,
    zone_id=config.ZONE_ID,
)
COMMAND_TOPIC = config.COMMAND_TOPIC_TEMPLATE.format(
    group_id=config.GROUP_ID,
    greenhouse_id=config.GREENHOUSE_ID,
    zone_id=config.ZONE_ID,
)

METRIC_SENSOR_IDS = {
    "temperature": "dht22-01",
    "air_humidity": "dht22-01",
    "soil_moisture": "soil-pot-01",
    "co2": "co2-pot-01",
    "light": "light-pot-01",
    "pump_state": "pump-led-01",
    "fan_power": "fan-led-01",
    "heater_power": "heater-led-01",
    "lamp_state": "lamp-led-01",
}

ACTUATOR_PINS = {
    "pump": Pin(config.PUMP_LED_PIN, Pin.OUT),
    "fan": Pin(config.FAN_LED_PIN, Pin.OUT),
    "heater": Pin(config.HEATER_LED_PIN, Pin.OUT),
    "lamp": Pin(config.LAMP_LED_PIN, Pin.OUT),
}
ACTUATOR_STATES = {
    "pump": 0,
    "fan": 0,
    "heater": 0,
    "lamp": 0,
}

DHT_SENSOR = dht.DHT22(Pin(config.DHT_PIN))
SOIL_ADC = ADC(Pin(config.SOIL_PIN))
LIGHT_ADC = ADC(Pin(config.LIGHT_PIN))
CO2_ADC = ADC(Pin(config.CO2_PIN))
for adc in (SOIL_ADC, LIGHT_ADC, CO2_ADC):
    adc.atten(ADC.ATTN_11DB)


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi", config.WIFI_SSID)
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.25)
    print("Wi-Fi connected", wlan.ifconfig())


def sync_clock():
    if ntptime is None:
        print("NTP unavailable; using device uptime timestamps")
        return
    try:
        ntptime.settime()
        print("NTP clock synchronized")
    except Exception as exc:
        print("NTP sync failed; using fallback timestamp", exc)


def timestamp_iso():
    year, month, day, hour, minute, second, *_ = time.gmtime()
    if year < 2024:
        raise RuntimeError("Clock is not synchronized; telemetry timestamp would be rejected")
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (year, month, day, hour, minute, second)


def scale_adc(raw, out_min, out_max):
    return out_min + (raw / 4095) * (out_max - out_min)


def read_core_metrics():
    try:
        DHT_SENSOR.measure()
        temperature = float(DHT_SENSOR.temperature())
        air_humidity = float(DHT_SENSOR.humidity())
    except Exception as exc:
        print("DHT read failed; publishing fallback values", exc)
        temperature = 22.0
        air_humidity = 55.0

    soil_moisture = 100 - scale_adc(SOIL_ADC.read(), 0, 100)
    light = scale_adc(LIGHT_ADC.read(), 0, 1000)
    co2 = scale_adc(CO2_ADC.read(), 400, 1600)

    return {
        "temperature": round(temperature, 2),
        "air_humidity": round(air_humidity, 2),
        "soil_moisture": round(soil_moisture, 2),
        "co2": round(co2, 2),
        "light": round(light, 2),
    }


def telemetry_envelope(metric, value):
    now = timestamp_iso()
    return {
        "message_id": "%s-%s-%s" % (config.DEVICE_ID, metric, time.ticks_ms()),
        "qos": config.MQTT_QOS,
        "reading": {
            "group_id": config.GROUP_ID,
            "greenhouse_id": config.GREENHOUSE_ID,
            "zone_id": config.ZONE_ID,
            "sensor_id": METRIC_SENSOR_IDS.get(metric, config.DEVICE_ID),
            "metric": metric,
            "value": float(value),
            "quality": "ok",
            "timestamp": now,
        },
    }


def publish_metric(client, metric, value):
    payload = json.dumps(telemetry_envelope(metric, value), separators=(",", ":"))
    client.publish(TELEMETRY_TOPIC, payload, qos=config.MQTT_QOS)
    print("Published", TELEMETRY_TOPIC, payload)


def publish_all_telemetry(client):
    for metric, value in read_core_metrics().items():
        publish_metric(client, metric, value)
    publish_metric(client, "pump_state", ACTUATOR_STATES["pump"])
    publish_metric(client, "fan_power", ACTUATOR_STATES["fan"])
    publish_metric(client, "heater_power", ACTUATOR_STATES["heater"])
    publish_metric(client, "lamp_state", ACTUATOR_STATES["lamp"])


def apply_command(command):
    command_id = command.get("command_id")
    target = (
        command.get("group_id"),
        command.get("greenhouse_id"),
        command.get("zone_id"),
    )
    actuator = command.get("actuator")
    action = command.get("action")
    value = command.get("value")
    duration_seconds = command.get("duration_seconds")
    source = command.get("source")
    reason = command.get("reason")

    if target != (config.GROUP_ID, config.GREENHOUSE_ID, config.ZONE_ID):
        print("Ignoring command for different target", command_id, target)
        return
    if actuator not in ACTUATOR_PINS:
        print("Ignoring invalid actuator command", command_id, actuator)
        return
    if action not in ("on", "off", "set_power"):
        print("Ignoring invalid action command", command_id, action)
        return

    pin = ACTUATOR_PINS[actuator]
    enabled = action == "on" or (action == "set_power" and (value or 0) > 0)
    if action == "off":
        enabled = False
    pin.value(1 if enabled else 0)
    ACTUATOR_STATES[actuator] = int(value or 100) if enabled and action == "set_power" else int(enabled)
    print(
        "Applied command",
        command_id,
        actuator,
        action,
        "duration_seconds=",
        duration_seconds,
        "source=",
        source,
        "reason=",
        reason,
    )


def on_command(topic, payload):
    try:
        command = json.loads(payload.decode("utf-8"))
    except (ValueError, TypeError) as exc:
        print("Malformed command payload ignored", topic, payload, exc)
        return

    if not isinstance(command, dict):
        print("Invalid command payload ignored; expected object", command)
        return

    missing = [field for field in ("actuator", "action") if field not in command]
    if missing:
        print("Invalid command payload ignored; missing", missing)
        return

    apply_command(command)


def mqtt_client():
    client = MQTTClient(
        client_id=config.DEVICE_ID,
        server=config.MQTT_HOST,
        port=config.MQTT_PORT,
        user=config.MQTT_USER or None,
        password=config.MQTT_PASSWORD or None,
        keepalive=config.MQTT_KEEPALIVE_SECONDS,
    )
    client.set_callback(on_command)
    client.connect()
    client.subscribe(COMMAND_TOPIC, qos=1)
    print("MQTT connected; subscribed to", COMMAND_TOPIC)
    return client


def main():
    connect_wifi()
    sync_clock()
    client = mqtt_client()
    last_publish = 0

    while True:
        try:
            client.check_msg()
            now = time.time()
            if now - last_publish >= config.PUBLISH_INTERVAL_SECONDS:
                publish_all_telemetry(client)
                last_publish = now
            time.sleep(0.1)
        except Exception as exc:
            print("MQTT loop error; reconnecting", exc)
            time.sleep(2)
            client = mqtt_client()


main()
