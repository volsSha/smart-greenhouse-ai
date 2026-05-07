# AI Agent

## Core Principle

The LLM agent has **no direct access to MQTT or actuators**. It uses tool calling to gather data, analyze state, and propose actions. All physical commands pass through FastAPI safety validation.

## Tool Categories

### Read-Only Tools (safe, autonomous)

| Tool                              | Description                               |
|-----------------------------------|-------------------------------------------|
| `get_greenhouse_context`          | Greenhouse metadata and configuration     |
| `get_plants`                      | List plants in greenhouse                 |
| `get_plant_profile`               | Optimal conditions for a plant species    |
| `get_latest_telemetry`            | Current sensor readings                   |
| `get_today_telemetry_summary`     | Aggregated stats for today                |
| `get_telemetry_range`             | Historical data for a time range          |
| `get_active_alerts`               | Current unresolved alerts                 |
| `get_recent_commands`             | Recent control command history            |
| `search_plant_knowledge`          | RAG search in plant knowledge base        |

### Intent Tools (create proposals, no direct action)

| Tool                      | Description                              |
|---------------------------|------------------------------------------|
| `propose_watering`        | Propose pump activation                  |
| `propose_ventilation`     | Propose fan activation                   |
| `propose_lighting`        | Propose lamp activation                  |
| `propose_setpoint_change` | Propose target parameter change          |

### Restricted Action Tools (require validation)

| Tool               | Description                       |
|--------------------|-----------------------------------|
| `execute_command`  | Execute validated command         |
| `cancel_command`   | Cancel pending command            |

## Agent Loop

```
User message
  -> System prompt + tools sent to OpenRouter
  -> Model responds with tool calls
  -> For each tool call:
       Execute tool locally
       Log tool call to ai_tool_calls table
       Return result to model
  -> Model may call more tools or produce final answer
  -> If answer contains proposed_action:
       Show in UI with Approve/Reject buttons
       On approve: FastAPI validates -> MQTT command
```

## System Prompt

```
You are the assistant of a small greenhouse control system.

Your tasks:
- analyze plant state based on actual telemetry
- never fabricate metrics
- use tools to retrieve data
- explain state in simple language
- distinguish fact, assumption, and recommendation
- never execute physical commands directly
- create proposed actions for any control suggestion
- if data is insufficient, explicitly say what data is missing

Forbidden:
- claiming plants are healthy without telemetry
- directly activating pump, fan, heater, or lamp
- ignoring safety rules
- recommending actions outside system limits
```

## Structured Response Format

```json
{
  "status": "warning",
  "summary": "Plants are generally fine, but soil is dry.",
  "observations": [
    "Temperature peaked at 31.2C today",
    "Soil moisture dropped to 21%",
    "CO2 within acceptable range"
  ],
  "recommendations": [
    "Water plants with short cycle",
    "Check soil sensor if values don't change after watering"
  ],
  "proposed_actions": [
    {
      "actuator": "pump",
      "action": "on",
      "duration_seconds": 30,
      "requires_confirmation": true
    }
  ]
}
```

## Explainability

Every tool call is logged in `ai_tool_calls` with:
- tool name and arguments
- result
- status and errors
- timestamp

UI shows which tools were used for each AI response:
```
AI used:
- get_plants
- get_today_telemetry_summary
- get_active_alerts
- search_plant_knowledge
```

## Code Structure

```
services/ai_agent/
  app/
    main.py
    agent.py
    openrouter_client.py
    prompts.py
    tools/
      telemetry_tools.py
      plant_tools.py
      alert_tools.py
      rag_tools.py
      command_tools.py
    schemas/
      tool_schemas.py
      agent_response.py
      command_intent.py
    memory/
      conversation_store.py
      tool_log_store.py
```
