# Wokwi Greenhouse Zone MicroPython Firmware

This folder contains the hosted Wokwi ESP32 MicroPython simulator for one greenhouse zone. It publishes telemetry to the local Docker Mosquitto broker and subscribes to approved actuator commands from the app.

Hosted Wokwi runs outside your local Docker network, so use an ngrok TCP tunnel for local development:

```text
Hosted Wokwi → ngrok TCP host:port → localhost:11883 → Docker Mosquitto
```

## Files

- `main.py` — MicroPython firmware entry point.
- `config.py` — editable Wi-Fi, MQTT broker, topic identity, and pin settings.
- `diagram.json` — Wokwi ESP32, DHT22, potentiometers, and actuator LEDs.

## Run locally with Docker Mosquitto and ngrok

1. Start the app stack from the repository root:

   ```bash
   docker compose up -d --build app mosquitto influxdb postgres
   ```

2. Confirm the local broker is reachable on host port `11883`. This is the host port mapped to the Mosquitto container's MQTT port.

3. Start a TCP tunnel to the host port:

   ```bash
   ngrok tcp 11883
   ```

4. Copy the forwarding host and port from ngrok. For example:

   ```text
   Forwarding  tcp://0.tcp.ngrok.io:12345 -> localhost:11883
   ```

5. Paste those values into `config.py`:

   ```python
   MQTT_HOST = "0.tcp.ngrok.io"
   MQTT_PORT = 12345
   ```

6. Keep the target identity in `config.py` aligned with the app command target:

   ```python
   GROUP_ID = "group-001"
   GREENHOUSE_ID = "gh-001"
   ZONE_ID = "zone-01"
   ```

7. Open the hosted Wokwi website, load this project folder, and start the simulation.

8. Open the app `/simulator` page, select **Wokwi / MQTT** mode, and watch the MQTT status panel.

## ngrok endpoint behavior

On the ngrok free tier, TCP forwarding host/port values can change whenever the tunnel is restarted. If Wokwi was working and then starts failing after a new ngrok session, assume the values in `config.py` are stale. Copy the current ngrok `tcp://host:port` into `MQTT_HOST` and `MQTT_PORT`, save the file, and restart the hosted Wokwi simulation.

Do not commit personal ngrok tokens, reserved domains, or production MQTT credentials.

## Verification checklist

- Docker Mosquitto is running and exposed on `localhost:11883`.
- `ngrok tcp 11883` is active and forwards to `localhost:11883`.
- `config.py` contains the current ngrok TCP host and port.
- Hosted Wokwi serial monitor shows Wi-Fi connected to `Wokwi-GUEST`.
- Hosted Wokwi serial monitor shows MQTT connected and subscribed to the `commands` topic.
- The app MQTT status panel receives telemetry from `group-001 / gh-001 / zone-01` or the identity configured in `config.py`.
- An approved app command for the same group, greenhouse, and zone appears in the Wokwi serial monitor.
- The expected virtual actuator LED changes state after a command.

## Troubleshooting

- **Connection refused:** make sure Mosquitto is running before starting ngrok, ngrok forwards to `localhost:11883`, and Wokwi uses the ngrok host/port rather than `localhost` or Docker service names. Hosted Wokwi cannot connect directly to your local `localhost`.
- **Stale ngrok host:** restart or inspect ngrok, copy the current `tcp://host:port` into `config.py`, then restart the Wokwi simulation. Free-tier ngrok TCP endpoints are not stable across sessions.
- **Wrong target zone:** commands are ignored when `group_id`, `greenhouse_id`, or `zone_id` do not match `GROUP_ID`, `GREENHOUSE_ID`, and `ZONE_ID` in `config.py`. Update the firmware identity or send the command to the matching app target.
- **No telemetry in the app:** confirm the app is in **Wokwi / MQTT** mode, the MQTT status panel is watching the same target identity, and the Wokwi serial monitor shows telemetry publishes without MQTT errors.
- **Auth failures:** if local Mosquitto authentication is enabled, set matching demo credentials in `MQTT_USER` and `MQTT_PASSWORD`. Keep real credentials out of this repository.
