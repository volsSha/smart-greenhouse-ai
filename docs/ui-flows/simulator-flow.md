# Simulator Flow

The simulator page is implemented in `app/ui/pages/simulator.py`. It controls the internal simulated telemetry loop and displays live zone state through `app/ui/components/zone_visualization.py`.

## Start Flow

```text
Open /simulator
  -> GET /api/simulator/status
  -> GET /api/settings
  -> render current simulator status and persisted control mode
  -> user selects scenario
     -> Normal | Dry Soil | Overheating | Low Light | Sensor Fault
  -> user sets topology
     -> groups count
     -> greenhouses per group
     -> zones per greenhouse
     -> interval seconds
  -> user clicks Start Simulator
     -> page checks selected simulator UI mode
        -> if Wokwi / MQTT selected: show warning and do not start
     -> page checks persisted control_mode
        -> if control_mode = mqtt: show warning and do not start
     -> POST /api/simulator/start
        -> simulator service creates/runs scoped zone state
        -> page refreshes status
        -> live visualization starts polling
```

## Stop Flow

```text
User clicks Stop Simulator
  -> POST /api/simulator/stop
  -> simulator stops runtime loop
  -> page refreshes status
  -> live zone polling stops or shows inactive state
```

## Live Zone Visualization

```text
Simulator running
  -> every 2 seconds
     -> GET /api/simulator/zones
     -> ZoneVisualization updates metric badges
     -> actuator icons reflect pump/fan/heater/lamp state
     -> scenario-driven warnings appear as status styling
```

## MQTT Mode Display

```text
User selects Wokwi / MQTT mode on /simulator
  -> page does not start internal simulator
  -> MQTTStatusPanel renders
     -> every 3 seconds
        -> GET /api/mqtt/status
        -> show broker connection, host, port, and health details
```

## Guard Rails

```text
Persisted control_mode = mqtt
  -> internal simulator start is blocked
  -> user is directed to /settings to switch to Internal simulator

Selected page mode = Wokwi / MQTT
  -> Start Simulator is blocked
  -> real telemetry should arrive from Wokwi/edge devices through MQTT
```

## Related Files

- `app/ui/pages/simulator.py`
- `app/api/simulator.py`
- `app/api/simulator_state.py`
- `app/api/mqtt_status.py`
- `app/services/simulator/zone_state.py`
- `app/ui/components/zone_visualization.py`
- `app/ui/components/mqtt_status_panel.py`