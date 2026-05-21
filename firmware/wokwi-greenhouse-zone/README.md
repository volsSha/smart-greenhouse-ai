# Wokwi Greenhouse Zone MicroPython Firmware

This folder contains the hosted Wokwi ESP32 MicroPython simulator for one greenhouse zone. It publishes telemetry to a public MQTT broker and subscribes to approved actuator commands from the app.

Recommended connection path:

```text
Hosted Wokwi → public Mosquitto broker on VPS → FastAPI app MQTT runtime
```

Hosted Wokwi cannot connect to your local Docker `localhost`, so use a public broker such as Mosquitto deployed on a VPS. See `docs/deploy-mosquitto-vps.md` for the broker deployment guide.

## Files

- `main.py` — MicroPython firmware entry point.
- `config.py` — editable Wi-Fi, MQTT broker, topic identity, and pin settings.
- `diagram.json` — Wokwi ESP32, DHT22, potentiometers, and actuator LEDs.

## Configure hosted Wokwi

1. Deploy or choose a public MQTT broker.

   Recommended endpoint shape:

   ```text
   mqtt.example.com:8883
   ```

2. Paste broker settings into `config.py`:

   ```python
   MQTT_HOST = "mqtt.example.com"
   MQTT_PORT = 8883
   MQTT_USER = "wokwi"
   MQTT_PASSWORD = "change-this-wokwi-password"
   ```

3. Keep the target identity in `config.py` aligned with the app command target:

   ```python
   GROUP_ID = "group-001"
   GREENHOUSE_ID = "gh-001"
   ZONE_ID = "zone-01"
   ```

4. Open the hosted Wokwi website, load this project folder, and start the simulation.

5. Open the app `/simulator` page, select **Wokwi / MQTT** mode, and watch the MQTT status panel.

## Pinout

| Part | ESP32 pin | Firmware role |
|---|---:|---|
| DHT22 SDA | D15 | Temperature and air-humidity readings |
| Soil potentiometer SIG | D34 | Soil-moisture simulation |
| Light potentiometer SIG | D35 | Light simulation |
| CO2 potentiometer SIG | D32 | CO2 simulation |
| Pump LED anode | D25 | Pump actuator visualization |
| Fan LED anode | D26 | Fan actuator visualization |
| Heater LED anode | D27 | Heater actuator visualization |
| Lamp LED anode | D14 | Lamp actuator visualization |

Ukrainian architecture, flow, and image-generation docs for this Wokwi integration are in `docs/llm-upload-uk/`.

## Verification checklist

- Public Mosquitto is reachable from the internet.
- `config.py` contains the public MQTT broker host, port, and Wokwi credentials.
- Hosted Wokwi serial monitor shows Wi-Fi connected to `Wokwi-GUEST`.
- Hosted Wokwi serial monitor shows MQTT connected and subscribed to the `commands` topic.
- The app MQTT status panel receives telemetry from `group-001 / gh-001 / zone-01` or the identity configured in `config.py`.
- An approved app command for the same group, greenhouse, and zone appears in the Wokwi serial monitor.
- The expected virtual actuator LED changes state after a command.

## Troubleshooting

- **Connection refused:** verify DNS, firewall, broker listener port, and credentials. Hosted Wokwi must use the public broker host rather than `localhost` or Docker service names.
- **TLS fails:** verify the certificate covers the broker hostname and that firmware/client TLS settings match the broker port.
- **Wrong target zone:** commands are ignored when `group_id`, `greenhouse_id`, or `zone_id` do not match `GROUP_ID`, `GREENHOUSE_ID`, and `ZONE_ID` in `config.py`. Update the firmware identity or send the command to the matching app target.
- **No telemetry in the app:** confirm the app is in **Wokwi / MQTT** mode, the app connects to the same public broker, and the Wokwi serial monitor shows telemetry publishes without MQTT errors.
- **Auth failures:** set matching demo credentials in `MQTT_USER` and `MQTT_PASSWORD`. Keep real credentials out of this repository.
