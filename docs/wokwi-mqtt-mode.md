# Wokwi / MQTT Mode

This mode connects the FastAPI app to a hosted Wokwi ESP32 MicroPython greenhouse-zone simulator over MQTT. Hosted Wokwi cannot reach your machine's `localhost` directly, so use a public MQTT broker that both Wokwi and the app can reach.

Recommended path:

```text
Hosted Wokwi ESP32 MicroPython → public Mosquitto broker on VPS → FastAPI app MQTT runtime
```

For the VPS broker setup, see `docs/deploy-mosquitto-vps.md`.

## Setup

1. Deploy or choose a public MQTT broker.

   Recommended endpoint shape:

   ```text
   mqtt.example.com:8883
   ```

   Use TLS on `8883` for real deployments. Plain `1883` is acceptable only for short local/private testing.

2. Configure the app to connect to that broker:

   ```env
   MQTT_HOST=mqtt.example.com
   MQTT_PORT=8883
   MQTT_USERNAME=app
   MQTT_PASSWORD=change-this-app-password
   ```

3. Start or restart the app stack:

   ```bash
   docker compose up -d --build app influxdb postgres
   ```

   If the broker is on a VPS, the local `mosquitto` service is optional for Wokwi mode.

4. Paste the same public broker endpoint into `firmware/wokwi-greenhouse-zone/config.py`:

   ```python
   MQTT_HOST = "mqtt.example.com"
   MQTT_PORT = 8883
   MQTT_USER = "wokwi"
   MQTT_PASSWORD = "change-this-wokwi-password"
   ```

5. Keep the firmware target identity aligned with the app command target:

   ```python
   GROUP_ID = "group-001"
   GREENHOUSE_ID = "gh-001"
   ZONE_ID = "zone-01"
   ```

6. Open the hosted Wokwi website and load the firmware project:

   ```text
   firmware/wokwi-greenhouse-zone
   ```

   The project is MicroPython-first. The editable broker settings live in `config.py`, and the firmware entry point is `main.py`.

7. Start the Wokwi simulation. The serial monitor should show Wi-Fi connecting to `Wokwi-GUEST`, then MQTT connecting and subscribing to the command topic.

8. In the app, open `/simulator` and select **Wokwi / MQTT** mode.

9. Watch the MQTT status panel for connection and telemetry updates.

10. Use AI chat or the Control page to approve a command. The command is published to MQTT and should appear in the Wokwi serial monitor.

## Verification checklist

- Public Mosquitto is running and reachable from the internet.
- DNS points `mqtt.example.com` to the broker VPS.
- Firewall allows the MQTT listener port, preferably `8883` only.
- App `.env` contains the public broker host, port, and `app` credentials.
- `firmware/wokwi-greenhouse-zone/config.py` contains the same public broker host/port and `wokwi` credentials.
- Hosted Wokwi is running the MicroPython project from `firmware/wokwi-greenhouse-zone`.
- Wokwi serial monitor shows Wi-Fi connected, MQTT connected, and subscription to the `commands` topic.
- The app MQTT status panel receives telemetry for the expected group, greenhouse, and zone.
- An approved command for that same target zone appears in the Wokwi serial monitor and toggles the matching virtual actuator LED.

## Canonical topics

All topics use this hierarchy:

```text
greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/{channel}
```

Channels:

- `telemetry` — device → app sensor readings
- `commands` — app → device actuator commands
- `state` — device → app actuator/device state
- `alerts` — reserved for alerts

Example command topic:

```text
greenhouse-groups/group-001/greenhouses/gh-001/zones/zone-01/commands
```

Example telemetry topic:

```text
greenhouse-groups/group-001/greenhouses/gh-001/zones/zone-01/telemetry
```

## Telemetry payload

Each telemetry message is a `TelemetryEnvelope` containing one metric reading:

```json
{
  "message_id": "wokwi-zone-01-temperature-1",
  "qos": 0,
  "reading": {
    "group_id": "group-001",
    "greenhouse_id": "gh-001",
    "zone_id": "zone-01",
    "sensor_id": "dht22-01",
    "metric": "temperature",
    "value": 24.5,
    "quality": "ok",
    "timestamp": "2026-05-11T12:00:00Z"
  }
}
```

## Command payload

Approved MQTT-mode commands are published with QoS 1:

```json
{
  "command_id": "...",
  "group_id": "...",
  "greenhouse_id": "...",
  "zone_id": "...",
  "actuator": "pump",
  "action": "on",
  "value": null,
  "duration_seconds": 30,
  "source": "ai_agent",
  "reason": "Needs water"
}
```

The MicroPython firmware ignores commands whose `group_id`, `greenhouse_id`, or `zone_id` do not match `config.py`.

## Wokwi pinout

| Wokwi part | ESP32 pin | Purpose |
|---|---:|---|
| DHT22 SDA | D15 | `temperature`, `air_humidity` |
| Soil potentiometer SIG | D34 | `soil_moisture` |
| Light potentiometer SIG | D35 | `light` |
| CO2 potentiometer SIG | D32 | `co2` |
| Pump LED anode | D25 | `pump_state` / pump command visualization |
| Fan LED anode | D26 | `fan_power` / fan command visualization |
| Heater LED anode | D27 | `heater_power` / heater command visualization |
| Lamp LED anode | D14 | `lamp_state` / lamp command visualization |

The Wokwi project source is `firmware/wokwi-greenhouse-zone/diagram.json`. Ukrainian diagram prompts and upload-ready architecture docs are in `docs/llm-upload-uk/`.

## Command status semantics

In v1, `executed` means the backend successfully published the command to MQTT. It does not mean the ESP32 confirmed receipt or actuation. Device acknowledgements are deferred follow-up work.

Recommended future acknowledgement flow:

```text
backend publishes command_id -> ESP32 receives and applies -> ESP32 publishes state/ack -> backend marks device_confirmed or device_failed
```

## Troubleshooting

- **Connection refused in Wokwi serial monitor:** verify DNS, firewall, broker container status, listener port, and credentials. Hosted Wokwi must use the public broker host, not `localhost` or Docker service names.
- **TLS connection fails:** verify the certificate covers the broker hostname and that firmware/client TLS settings match the broker port.
- **Telemetry arrives but commands do not affect the Wokwi device:** verify the firmware `GROUP_ID`, `GREENHOUSE_ID`, and `ZONE_ID` match the command target shown in the app. A wrong target zone is intentionally ignored by the firmware.
- **No telemetry in the app status panel:** check the Wokwi serial monitor for MQTT connection errors, confirm the app is in **Wokwi / MQTT** mode, and confirm the app connects to the same broker as Wokwi.
- **Payloads are rejected or ignored:** compare the command topic and payload with the canonical examples above; malformed JSON and unsupported actuators/actions are logged and ignored so the firmware can continue running.
- **Using Mosquitto auth:** configure matching credentials in both the app `.env` and firmware `MQTT_USER` / `MQTT_PASSWORD`. Do not commit real credentials.
