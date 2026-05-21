# 04. Приклади топологій, topics, payloads і політик

## Приклад 1: мала домашня група

```text
group-home-001
  greenhouse gh-balcony
    zone zone-tomatoes
      plant: tomato / flowering
      sensors: temperature, air_humidity, soil_moisture, light
      actuators: pump, fan, lamp
    zone zone-lettuce
      plant: lettuce / vegetative
      sensors: temperature, air_humidity, soil_moisture, light
      actuators: pump, lamp
```

Сценарій:

- зона томатів має нижчу межу вологості ґрунту 45%;
- зона салату потребує менш інтенсивного світла;
- AI на group scope має порівняти ризики й пріоритизувати томати, якщо soil_moisture < threshold.

## Приклад 2: навчальна Wokwi-група

```text
group-demo-001
  greenhouse gh-001
    zone zone-01
      edge-node: wokwi-esp32-zone-01
      DHT22: temperature + air_humidity
      potentiometer D34: soil_moisture
      potentiometer D35: light
      potentiometer D32: co2
      LEDs:
        D25 pump
        D26 fan
        D27 heater
        D14 lamp
```

Це canonical demo topology для Wokwi.

## Приклад 3: кілька теплиць і зон

```text
group-farm-001
  greenhouse gh-001
    zone zone-01 tomatoes
    zone zone-02 cucumbers
  greenhouse gh-002
    zone zone-01 peppers
    zone zone-02 lettuce
  greenhouse gh-003
    zone zone-01 seedlings
```

AI group-level питання:

```text
Порівняй усі теплиці в group-farm-001 і покажи, де треба втручання сьогодні.
```

Очікувана поведінка AI:

- викликати group overview;
- отримати today summaries;
- порівняти теплиці;
- перевірити active alerts;
- не вигадувати дані;
- запропонувати scoped actions тільки для конкретних зон.

## MQTT topics

### Telemetry

```text
greenhouse-groups/group-demo-001/greenhouses/gh-001/zones/zone-01/telemetry
```

### Commands

```text
greenhouse-groups/group-demo-001/greenhouses/gh-001/zones/zone-01/commands
```

### State / acknowledgements майбутнього розширення

```text
greenhouse-groups/group-demo-001/greenhouses/gh-001/zones/zone-01/state
```

## Telemetry payload: температура

```json
{
  "message_id": "wokwi-zone-01-temperature-0001",
  "qos": 0,
  "reading": {
    "group_id": "group-demo-001",
    "greenhouse_id": "gh-001",
    "zone_id": "zone-01",
    "sensor_id": "dht22-01",
    "metric": "temperature",
    "value": 24.5,
    "quality": "ok",
    "timestamp": "2026-05-21T12:00:00Z"
  }
}
```

## Telemetry payload: вологість ґрунту

```json
{
  "message_id": "wokwi-zone-01-soil-0001",
  "qos": 0,
  "reading": {
    "group_id": "group-demo-001",
    "greenhouse_id": "gh-001",
    "zone_id": "zone-01",
    "sensor_id": "soil-pot-01",
    "metric": "soil_moisture",
    "value": 34.0,
    "quality": "ok",
    "timestamp": "2026-05-21T12:00:05Z"
  }
}
```

## Command payload: насос увімкнути на 30 секунд

```json
{
  "command_id": "cmd-20260521-0001",
  "group_id": "group-demo-001",
  "greenhouse_id": "gh-001",
  "zone_id": "zone-01",
  "actuator": "pump",
  "action": "on",
  "value": null,
  "duration_seconds": 30,
  "source": "ai_agent",
  "reason": "Soil moisture is below the tomato profile minimum."
}
```

## Command payload: вентилятор 75%

```json
{
  "command_id": "cmd-20260521-0002",
  "group_id": "group-demo-001",
  "greenhouse_id": "gh-001",
  "zone_id": "zone-01",
  "actuator": "fan",
  "action": "set_power",
  "value": 75,
  "duration_seconds": 300,
  "source": "control_engine",
  "reason": "Temperature is above the zone setpoint maximum."
}
```

## Suggested GroupControlPolicy JSON

Це рекомендований формат для документації й майбутньої формалізації. Він описує group-level правила, які safety layer і control engine можуть враховувати перед виконанням команд.

```json
{
  "version": 1,
  "priority": 100,
  "applies_to": {
    "greenhouse_ids": ["*"],
    "zone_ids": ["*"]
  },
  "watering": {
    "enabled": true,
    "max_duration_seconds": 60,
    "cooldown_seconds": 300,
    "min_soil_moisture_before_block": 70,
    "forbid_if_recent_rain_detected": false
  },
  "ventilation": {
    "enabled": true,
    "max_power": 100,
    "max_duration_seconds": 600,
    "prefer_over_heating_conflict": true
  },
  "heating": {
    "enabled": true,
    "max_power": 80,
    "max_duration_seconds": 300,
    "forbidden_if_temperature_above": 28
  },
  "lighting": {
    "enabled": true,
    "max_duration_seconds": 3600,
    "quiet_hours": {
      "start": "22:00",
      "end": "06:00"
    }
  },
  "approval": {
    "require_manual_confirmation": true,
    "allow_control_engine_auto_propose": true,
    "allow_ai_propose": true
  }
}
```

## Suggested watering strategy

```text
Inputs:
  - latest soil_moisture
  - plant profile min/max soil moisture
  - growth stage
  - last pump command timestamp
  - command cooldown
  - group watering policy

Decision:
  if soil_moisture < profile.min - 10:
      severity = critical
      propose pump on 30-60 seconds
  else if soil_moisture < profile.min:
      severity = warning
      propose pump on 15-30 seconds
  else:
      no watering proposal

Never:
  - run pump longer than safety max
  - repeat pump command inside cooldown
  - water without zone scope
  - water if sensor data is missing/stale
```

## Suggested lighting strategy

```text
Inputs:
  - latest light value
  - plant profile light range
  - local day/night schedule
  - quiet hours policy
  - lamp max duration

Decision:
  if light < profile.min and outside quiet hours:
      propose lamp on 10-30 minutes
  if light is sufficient:
      no lamp proposal
  if temperature too high:
      avoid lamp if it can increase heat load
```

## Suggested ventilation strategy

```text
Inputs:
  - latest temperature
  - latest air_humidity
  - CO2 trend
  - plant profile temperature max
  - fan actuator capabilities

Decision:
  if temperature > max:
      propose fan set_power 50-75%
  if humidity very high:
      propose ventilation if temperature not too low
  if heater is active:
      check conflict before fan proposal
```

## Suggested AI response example

```json
{
  "scope": {
    "level": "zone",
    "group_id": "group-demo-001",
    "greenhouse_id": "gh-001",
    "zone_id": "zone-01"
  },
  "status": "warning",
  "summary": "У zone-01 вологість ґрунту нижча за рекомендований діапазон для томатів.",
  "observations": [
    "Останнє значення soil_moisture: 34%.",
    "Температура 24.5°C у межах допустимого діапазону.",
    "Активних критичних алертів для вентиляції немає."
  ],
  "recommendations": [
    "Перевірити, чи датчик вологості стабільно передає дані.",
    "Запропонувати короткий полив і повторно оцінити soil_moisture після наступних telemetry readings."
  ],
  "proposed_actions": [
    {
      "group_id": "group-demo-001",
      "greenhouse_id": "gh-001",
      "zone_id": "zone-01",
      "actuator": "pump",
      "action": "on",
      "duration_seconds": 30,
      "reason": "Soil moisture is below the tomato profile minimum.",
      "requires_confirmation": true
    }
  ]
}
```

## Wokwi pinout summary

| Wokwi part | ESP32 pin | Призначення |
|---|---:|---|
| DHT22 SDA | D15 | Температура + вологість повітря |
| Soil potentiometer SIG | D34 | Вологість ґрунту |
| Light potentiometer SIG | D35 | Освітленість |
| CO2 potentiometer SIG | D32 | CO2 simulation |
| Pump LED anode | D25 | Візуалізація насоса |
| Fan LED anode | D26 | Візуалізація вентилятора |
| Heater LED anode | D27 | Візуалізація нагрівача |
| Lamp LED anode | D14 | Візуалізація лампи |
