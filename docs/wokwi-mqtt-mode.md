# Wokwi / MQTT Mode

This mode connects the FastAPI app to a hosted Wokwi ESP32 MicroPython greenhouse-zone simulator over MQTT. Hosted Wokwi cannot reach your machine's `localhost` directly, so the local development path is:

```text
Hosted Wokwi ESP32 MicroPython → ngrok TCP → localhost:11883 → Docker Mosquitto → FastAPI app
```

## Local setup

1. Start the app stack and local broker:

   ```bash
   docker compose up -d --build app mosquitto influxdb postgres
   ```

2. Confirm Mosquitto is reachable from the host on port `11883`. The Docker broker listens inside the container on MQTT port `1883`, but the local host port used by Wokwi/ngrok is `11883`.

3. Start an ngrok TCP tunnel to the local Mosquitto host port:

   ```bash
   ngrok tcp 11883
   ```

4. Copy the generated ngrok forwarding host and port from the `tcp://...` URL. For example, if ngrok prints:

   ```text
   Forwarding  tcp://0.tcp.ngrok.io:12345 -> localhost:11883
   ```

   then use:

   ```python
   MQTT_HOST = "0.tcp.ngrok.io"
   MQTT_PORT = 12345
   ```

5. Paste those values into `firmware/wokwi-greenhouse-zone/config.py`. Keep the device identity aligned with the app target zone:

   ```python
   GROUP_ID = "group-001"
   GREENHOUSE_ID = "gh-001"
   ZONE_ID = "zone-01"
   ```

   ngrok free-tier TCP host/port values are usually not stable. If you stop and restart ngrok, treat any old `MQTT_HOST` / `MQTT_PORT` values in `config.py` as stale and copy the new forwarding host/port before running Wokwi again.

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

- Docker Mosquitto is running and exposed on local host port `11883`.
- `ngrok tcp 11883` is running and forwards to `localhost:11883`.
- `firmware/wokwi-greenhouse-zone/config.py` contains the current ngrok TCP host and port, not an old tunnel value.
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
  "value": 50.0,
  "duration_seconds": 30,
  "source": "ai_agent",
  "reason": "Needs water"
}
```

The MicroPython firmware ignores commands whose `group_id`, `greenhouse_id`, or `zone_id` do not match `config.py`.

## Command status semantics

In v1, `executed` means the backend successfully published the command to MQTT. It does not mean the ESP32 confirmed receipt or actuation. Device acknowledgements are deferred follow-up work.

## Troubleshooting

- **Connection refused in Wokwi serial monitor:** verify Docker Mosquitto is running, the broker is published on host port `11883`, and ngrok is forwarding to `localhost:11883` rather than container port `1883`. Restart the broker and ngrok tunnel if the tunnel was created before Mosquitto was listening.
- **Stale ngrok host or port:** free-tier ngrok TCP endpoints can change between sessions. Copy the current `tcp://host:port` values from the active ngrok output into `firmware/wokwi-greenhouse-zone/config.py`, then restart the hosted Wokwi simulation.
- **Telemetry arrives but commands do not affect the Wokwi device:** verify the firmware `GROUP_ID`, `GREENHOUSE_ID`, and `ZONE_ID` match the command target shown in the app. A wrong target zone is intentionally ignored by the firmware.
- **No telemetry in the app status panel:** check the Wokwi serial monitor for MQTT connection errors, confirm the app is in **Wokwi / MQTT** mode, and confirm the tunnel points at local host port `11883`.
- **Payloads are rejected or ignored:** compare the command topic and payload with the canonical examples above; malformed JSON and unsupported actuators/actions are logged and ignored so the firmware can continue running.
- **Using Mosquitto auth:** configure matching local development credentials in both the app `.env` and firmware `MQTT_USER` / `MQTT_PASSWORD`. Do not commit real credentials or ngrok auth tokens.
