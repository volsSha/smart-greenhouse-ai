# 01. Огляд системи Smart Greenhouse AI

## Призначення

Smart Greenhouse AI — система керування групою малих теплиць із підтримкою IoT, MQTT, телеметрії, візуального операційного інтерфейсу, AI-аналізу, RAG-знань і безпечного workflow для фізичних команд.

Система не моделює одну ізольовану теплицю. Базова одиниця масштабу — **група теплиць**, у якій є кілька теплиць, а кожна теплиця має кілька зон вирощування.

```text
Група теплиць
  ├── Теплиця 1
  │     ├── Зона 1: томати, сенсори, насос, вентилятор, лампа
  │     └── Зона 2: салат, інший мікроклімат
  └── Теплиця 2
        ├── Зона 1: огірки
        └── Зона 2: перець
```

## Основні архітектурні принципи

1. **AI не виконує фізичні команди напряму.** LLM може аналізувати дані та створювати пропозиції, але не має прямого доступу до MQTT або актуаторів.
2. **Кожна дія має область дії.** Команда завжди містить `group_id`, `greenhouse_id`, `zone_id` і цільовий актуатор.
3. **Безпека перед виконанням.** FastAPI повторно перевіряє стан зони, політики групи, cooldown-и й межі актуаторів перед публікацією MQTT-команди.
4. **Телеметрія і доменна модель розділені.** InfluxDB зберігає часові ряди; PostgreSQL зберігає групи, теплиці, зони, пристрої, рослини, команди, алерти, AI-історію й RAG.
5. **Реальні пристрої й симулятори мають однакову модель topics.** Внутрішній симулятор і ESP32/Wokwi працюють через ту саму scoped-ієрархію MQTT.

## Компоненти системи

| Компонент | Роль |
|---|---|
| NiceGUI UI | Панелі dashboard, zones, control, simulator, AI chat, RAG, logs, settings |
| FastAPI backend | REST API, валідація, safety layer, AI endpoint, MQTT runtime |
| Mosquitto MQTT | Брокер між ESP32/симулятором і backend |
| InfluxDB | Телеметрія мікроклімату: температура, вологість, CO2, світло, стан актуаторів |
| PostgreSQL + pgvector | Структурні дані, команди, алерти, AI conversations, RAG chunks/embeddings |
| Pydantic AI + OpenRouter | AI-агент із tool calling і structured response |
| Wokwi ESP32 MicroPython | Віртуальний edge-node з DHT22, потенціометрами й LED-актуаторами |
| Internal simulator | Python MQTT publisher для демонстраційних сценаріїв |
| Control engine | Rule-based observer/proposer, що створює пропозиції, а не публікує команди напряму |
| Worker | Фонові задачі: reindex/RAG/майбутні summary jobs |

## Доменна модель

```text
GreenhouseGroup 1 ── 1..* Greenhouse
Greenhouse 1 ── 1..* GreenhouseZone
Greenhouse 1 ── 0..* EdgeNode
GreenhouseZone 1 ── 0..* Sensor
GreenhouseZone 1 ── 0..* Actuator
GreenhouseZone 1 ── 0..* PlantBatch
PlantProfile 1 ── 0..* PlantBatch
GreenhouseZone 1 ── 0..* ControlSetpoint
GreenhouseZone 1 ── 0..* Alert
GreenhouseZone 1 ── 0..* CommandLog
GreenhouseGroup 1 ── 0..* GroupControlPolicy
GreenhouseGroup 1 ── 0..* RAGDocument
RAGDocument 1 ── 0..* RAGChunk
AIConversation 1 ── 0..* AIMessage
AIMessage 1 ── 0..* AIToolCall
```

## Рівні аналізу AI

AI-агент працює на трьох рівнях:

1. **Zone scope** — одна зона, її рослини, сенсори, актуатори, setpoints, алерти й recent commands.
2. **Greenhouse scope** — агрегований стан усіх зон однієї теплиці.
3. **Group scope** — порівняння теплиць і пріоритизація проблем у всій групі.

Приклад питань:

- `Що відбувається із зоною томатів у теплиці gh-001?`
- `Порівняй теплиці в group-001 і скажи, де найбільший ризик.`
- `Чи треба поливати zone-01? Якщо так — запропонуй безпечну дію.`

## Основний шлях даних

```text
ESP32/Wokwi або internal simulator
  -> MQTT telemetry topic
  -> Mosquitto
  -> FastAPI MQTTRuntime
  -> TelemetryIngestion validation
  -> InfluxDB microclimate measurement
  -> UI dashboard/control/AI tools
  -> AI аналізує дані й RAG
  -> AI створює proposed action
  -> користувач підтверджує
  -> FastAPI safety validation
  -> MQTT command topic
  -> ESP32/Wokwi або simulator застосовує стан актуатора
```

## MQTT topic model

```text
greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/{channel}
```

Канали:

- `telemetry` — сенсори й стан актуаторів від device до app.
- `commands` — підтверджені команди від app до device.
- `state` — майбутній канал для device acknowledgements/state sync.
- `alerts` — резерв для scoped-alert повідомлень.

## Контур безпеки фізичних дій

Будь-яка команда проходить state machine:

```text
proposed -> validated -> approved -> executing -> executed
                         └-> rejected / cancelled / expired / failed
```

Перевірки:

- чи існує group/greenhouse/zone/actuator;
- чи актуатор підтримує requested action;
- чи не перевищено максимальну тривалість або потужність;
- чи не активний cooldown;
- чи команда не конфліктує з поточним станом;
- чи не порушує group policy або zone setpoint;
- чи користувач явно підтвердив дію.

## ESP32/Wokwi модель зони

Одна Wokwi-зона імітує edge-node ESP32:

| Пристрій | Pin | Метрика / дія |
|---|---:|---|
| DHT22 | D15 | `temperature`, `air_humidity` |
| Soil potentiometer | D34 | `soil_moisture` |
| Light potentiometer | D35 | `light` |
| CO2 potentiometer | D32 | `co2` |
| Pump LED | D25 | `pump_state` / pump command |
| Fan LED | D26 | `fan_power` / fan command |
| Heater LED | D27 | `heater_power` / heater command |
| Lamp LED | D14 | `lamp_state` / lamp command |

## Що система має покривати далі

Під час review виявлені області, які варто документувати й розвивати:

- формальна схема `GroupControlPolicy.policy` JSON;
- поливна стратегія: thresholds, duty cycles, cooldowns, plant profile integration;
- світлова стратегія: денний цикл, DLI, minimum/maximum lamp duration;
- device acknowledgement flow: `command published` не дорівнює `actuator executed`;
- alert lifecycle: active/resolved/dismissed/escalated;
- інтеграція control engine як фонового observer job або telemetry-triggered evaluator;
- окремий rendered pinout/circuit для Wokwi ESP32.
