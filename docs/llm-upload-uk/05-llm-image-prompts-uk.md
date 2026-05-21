# 05. Промпти для генерації архітектурних зображень

Ці промпти можна передати LLM або image-generation model для створення презентаційних схем українською мовою. Усі підписи на зображеннях мають бути українською.

## Prompt 1: загальна архітектура системи

```text
Створи чисту технічну архітектурну діаграму українською мовою для системи "Smart Greenhouse AI".

Покажи такі блоки:
1. Операторський браузер з NiceGUI UI: Dashboard, Zones, Control, Simulator, AI Chat, RAG, Logs, Settings.
2. FastAPI backend: REST API, MQTT runtime, Telemetry ingestion, Command service, Safety validator, AI Agent, RAG service.
3. Mosquitto MQTT broker з двома потоками: telemetry від пристроїв до backend, commands від backend до пристроїв.
4. InfluxDB для microclimate time-series telemetry.
5. PostgreSQL + pgvector для груп, теплиць, зон, пристроїв, рослин, команд, алертів, AI conversations, RAG chunks.
6. Edge nodes: Wokwi ESP32, real ESP32, internal Python simulator.
7. OpenRouter/Pydantic AI як зовнішній LLM provider.

Головний меседж на діаграмі: AI НЕ керує пристроями напряму. Шлях команди: AI або оператор → proposed action → FastAPI safety validation → user approval → MQTT command.

Стиль: modern cloud architecture, світлий фон, синьо-зелена палітра, чіткі стрілки, українські labels, без зайвого тексту.
```

## Prompt 2: доменна модель групи теплиць

```text
Створи UML-style domain model diagram українською для Smart Greenhouse AI.

Покажи ієрархію:
- Група теплиць має багато теплиць.
- Теплиця має багато зон і edge nodes.
- Зона має сенсори, актуатори, партії рослин, setpoints, alerts, command logs.
- Профіль рослини пов'язаний із партією рослин.
- Група має group control policies і RAG documents.
- AI conversation має AI messages, AI message має tool calls.
- RAG document має RAG chunks з embeddings.

Підписи українською:
Група теплиць, Теплиця, Зона, Сенсор, Актуатор, Партія рослин, Профіль рослин, Налаштування цілей, Політика групи, Алерт, Команда, AI розмова, AI повідомлення, Виклик інструмента, RAG документ, RAG фрагмент.

Стиль: clean UML class diagram, мінімалістично, читабельно, без коду, з cardinality 1..*, 0..*.
```

## Prompt 3: Wokwi ESP32 зона

```text
Створи технічну схему Wokwi ESP32 greenhouse zone українською мовою.

Покажи ESP32 DevKit у центрі. Зліва покажи actuator LEDs:
- Pump LED синій на D25
- Fan LED блакитний на D26
- Heater LED червоний на D27
- Lamp LED жовтий на D14

Справа покажи sensors:
- DHT22 на D15 для температури і вологості повітря
- Soil potentiometer на D34 для вологості ґрунту
- Light potentiometer на D35 для освітленості
- CO2 potentiometer на D32 для CO2

Покажи MQTT flow:
ESP32 publish telemetry → Mosquitto broker → FastAPI app
FastAPI approved command → Mosquitto broker → ESP32 changes LED actuator

Підписи українською, але зберегти технічні назви pins і metrics: temperature, air_humidity, soil_moisture, light, co2, pump_state, fan_power, heater_power, lamp_state.

Стиль: educational IoT diagram, clean wiring, not photorealistic, suitable for README.
```

## Prompt 4: AI safety workflow

```text
Створи flow diagram українською для безпечного AI workflow у Smart Greenhouse AI.

Показати послідовність:
Користувач питає AI → AI викликає read-only tools → AI читає InfluxDB/PostgreSQL/RAG → AI формує structured response → AI створює proposed action → CommandService створює CommandLog → SafetyValidator перевіряє → UI показує approval card → оператор підтверджує → SafetyValidator перевіряє ще раз → CommandPublisher публікує MQTT command → ESP32/симулятор змінює актуатор.

Окремо виділити червоним "Заборонено": AI → MQTT напряму.
Окремо зеленим "Дозволено": AI → proposed action → safety → approval → MQTT.

Стиль: process flow, українські labels, чіткі кольори для safe/forbidden paths.
```

## Prompt 5: multi-greenhouse operations dashboard

```text
Створи концептуальну діаграму операційного dashboard для групи теплиць українською.

Показати:
- Верхній рівень: group overview із загальним статусом.
- Карти теплиць gh-001, gh-002, gh-003.
- Всередині кожної теплиці 2-3 зони.
- Кожна зона має mini telemetry: температура, вологість ґрунту, CO2, світло.
- Alerts badges: warning/critical.
- Шлях drill-down: group → greenhouse → zone.
- Action panel: pump, fan, heater, lamp, але з approval step.

Мова підписів: українська.
Стиль: UI wireframe + system explanation, clean, not too detailed.
```

## Prompt 6: data storage split

```text
Створи діаграму українською, яка пояснює розділення даних у Smart Greenhouse AI.

Ліва частина: InfluxDB "Часові ряди телеметрії".
Приклади: temperature, air_humidity, soil_moisture, co2, light, pump_state, fan_power, heater_power, lamp_state.
Tags: group_id, greenhouse_id, zone_id, sensor_id, metric.

Права частина: PostgreSQL + pgvector "Структурні та семантичні дані".
Приклади: groups, greenhouses, zones, sensors, actuators, plant profiles, plant batches, setpoints, policies, command logs, alerts, AI conversations, tool calls, RAG documents, RAG chunks, embeddings.

Посередині: FastAPI services читають обидва сховища для UI, AI tools і safety validation.
Стиль: clean data architecture diagram, українські labels, database icons.
```

## Prompt 7: future command acknowledgement extension

```text
Створи sequence diagram українською для майбутнього command acknowledgement у Smart Greenhouse AI.

Показати lifelines:
FastAPI CommandService, Mosquitto MQTT, ESP32/Wokwi, PostgreSQL CommandLog, NiceGUI UI.

Поточний v1 стан: executed означає "backend опублікував MQTT command", але не гарантує, що ESP32 реально виконав.
Майбутній flow:
1. CommandService publishes command_id на commands topic.
2. CommandLog state = published.
3. ESP32 receives command.
4. ESP32 validates target group_id/greenhouse_id/zone_id.
5. ESP32 applies actuator state.
6. ESP32 publishes state/ack with command_id and result.
7. FastAPI receives ack.
8. CommandLog state = device_confirmed або device_failed.
9. UI shows confirmed physical execution.

Стиль: technical sequence diagram, українські labels, clear distinction current vs future.
```

## Prompt 8: zones, motors, watering, lighting

```text
Створи детальну агротехнічну схему українською для однієї теплиці з кількома зонами.

Показати теплицю gh-001 із зонами:
- zone-01 Томати: pump, fan, heater, lamp, DHT22, soil sensor, light sensor, CO2 sensor.
- zone-02 Салат: pump, lamp, DHT22, soil sensor, light sensor.
- zone-03 Розсада: pump, heater, lamp, humidity sensor.

Показати, що кожна зона має власні setpoints і plant profile.
Показати, що group policy задає глобальні обмеження: pump max 60s, fan max 100%, heater forbidden above 28°C, lamp quiet hours 22:00-06:00.
Показати потоки:
Sensors → MQTT telemetry → InfluxDB → AI/control engine
AI/control engine → proposed action → approval → MQTT command → actuator.

Стиль: readable system + greenhouse hybrid diagram, українські labels, акцент на zones and actuators.
```

## Prompt 9: фізична електрична схема ESP32 + реле + багато зон

```text
Створи детальну фізичну wiring-схему українською для теплиці gh-001 з трьома зонами та двома ESP32.

Показати:
1. ESP32-A керує zone-01 і zone-02.
   - D25 -> relay CH1 -> pump_zone_01, 12V DC насос.
   - D26 -> relay CH2 -> fan_zone_01, 12V DC вентилятор.
   - D27 -> relay CH3 -> lamp_zone_01, grow lamp.
   - D14 -> relay CH4 -> pump_zone_02.
   - D33 -> relay CH5 -> fan_zone_02.
   - D32 -> relay CH6 -> lamp_zone_02.
2. ESP32-B керує zone-03 і shared devices.
   - D25 -> relay CH1 -> pump_zone_03.
   - D26 -> relay CH2 -> heater_zone_03.
   - D27 -> relay CH3 -> grow_lamp_zone_03.
   - D14 -> relay CH4 -> roof_fan_shared.
3. Sensor side:
   - soil sensors to ADC pins.
   - DHT22 sensors to digital pins.
   - light/CO2 analog sensors to ADC pins.
4. Power side:
   - 5V PSU для ESP32/relay logic.
   - 12V PSU для DC pumps/fans/LED strip.
   - 220V AC через RCD/circuit breaker/enclosed SSR або relay тільки для AC lamp/heater.
5. MQTT mapping:
   ESP32 publish telemetry to greenhouse-groups/{group}/greenhouses/{greenhouse}/zones/{zone}/telemetry.
   Backend publishes approved commands to corresponding commands topic.

Візуально розділити low-voltage control side і high-voltage/power side. Додати попередження: GPIO не живить насос напряму, GPIO керує тільки реле/SSR/MOSFET.
Стиль: technical wiring diagram, educational, clean, українські labels, pins and topics exact.
```

## Prompt 10: relay power path for pump/lamp/heater

```text
Створи три міні-схеми українською поруч:

1. 12V DC pump через mechanical relay:
ESP32 GPIO -> relay IN, 12V+ -> COM, NO -> pump +, pump - -> 12V-. Підпис: GPIO керує тільки реле, насос живиться окремим 12V PSU.

2. DC fan або LED strip через MOSFET/PWM:
ESP32 PWM GPIO -> MOSFET gate driver, load між 12V+ і MOSFET drain, source to 12V-, common GND. Підпис: підходить для fan set_power і dimming.

3. AC lamp/heater через SSR:
ESP32 GPIO -> SSR input, AC Live -> SSR -> lamp/heater Live, Neutral напряму до load, Ground до корпусу. Підпис: тільки сертифікований корпус, fuse, RCD/УЗО, ізоляція.

Стиль: електротехнічна навчальна схема, українські labels, не фотореалізм, чітке розділення low voltage і high voltage.
```
