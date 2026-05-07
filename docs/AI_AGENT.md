# AI Agent

## Core Principle

The LLM agent has **no direct access to MQTT or actuators**. It uses tool calling to gather group, greenhouse, zone, telemetry, plant, alert, command, and RAG data. All physical commands are scoped proposed actions that pass through FastAPI safety validation and user approval.

The agent can reason at three levels:

1. **Zone** - one greenhouse zone, its plants, sensors, actuators, setpoints, and alerts
2. **Greenhouse** - aggregate state across zones in one greenhouse
3. **Group** - aggregate state and comparison across all greenhouses in a group

## Tool Categories

### Read-Only Tools (safe, autonomous)

| Tool | Description |
|------|-------------|
| `get_group_overview(group_id)` | Group metadata, greenhouses, zones, and status summary |
| `get_greenhouses(group_id)` | List greenhouses in a group |
| `get_greenhouse_state(group_id, greenhouse_id)` | Greenhouse-level state and zone summary |
| `get_zone_state(group_id, greenhouse_id, zone_id)` | Zone metadata, plants, sensors, actuators, setpoints, and latest readings |
| `get_today_group_summary(group_id)` | Today's aggregated group telemetry summary |
| `get_today_greenhouse_summary(group_id, greenhouse_id)` | Today's greenhouse telemetry summary |
| `get_today_zone_summary(group_id, greenhouse_id, zone_id)` | Today's zone telemetry summary |
| `compare_greenhouses(group_id)` | Compare greenhouse microclimate and alert status |
| `get_active_alerts(group_id, greenhouse_id = null, zone_id = null)` | Active alerts filtered by scope |
| `get_recent_commands(group_id, greenhouse_id = null, zone_id = null)` | Recent command history filtered by scope |
| `search_plant_knowledge(query, group_id = null)` | RAG search in agronomic knowledge base |

### Proposed Action Tools (create proposals, no direct action)

| Tool | Description |
|------|-------------|
| `propose_action` | Propose scoped actuator command for group/greenhouse/zone |
| `propose_setpoint_change` | Propose scoped setpoint change |

`propose_action` requires:

```text
group_id
greenhouse_id
zone_id
actuator
action
duration_seconds
reason
```

### Restricted Action Tools

Restricted execution is handled by FastAPI command endpoints and the UI approval workflow, not by model-owned tools. Do not expose a model-callable `execute_command` unless it only resolves an existing approval request without publishing MQTT directly.

## Agent Loop

```text
User message with optional scope
  -> System prompt + group/greenhouse/zone-aware tools sent to model
  -> Model responds with tool calls
  -> For each tool call:
       Execute tool locally
       Log tool call to ai_tool_calls table
       Return result to model
  -> Model may call more tools or produce final structured answer
  -> If answer contains proposed_action:
       Store command proposal
       Show scoped approval card in UI
       On approve: FastAPI revalidates current zone/group state -> MQTT command
```

## System Prompt Principles

```text
You are the assistant for a greenhouse fleet control system.

Your tasks:
- analyze group, greenhouse, and zone state based on actual telemetry
- never fabricate metrics
- use tools to retrieve data
- explain whether you are talking about a group, greenhouse, or zone
- distinguish fact, assumption, and recommendation
- compare greenhouses only from available data
- prioritize problematic greenhouses or zones when asked about the group
- never execute physical commands directly
- create proposed actions for any control suggestion
- include group_id, greenhouse_id, and zone_id in every proposed physical action
- if data is insufficient, explicitly say what data is missing

Forbidden:
- claiming a group, greenhouse, zone, or plant batch is healthy without telemetry
- directly activating pump, fan, heater, or lamp
- ignoring safety rules or group policies
- recommending actions outside system limits
- hiding which tools were used
```

## Structured Response Format

```json
{
  "scope": {
    "level": "group",
    "group_id": "group-001",
    "greenhouse_id": null,
    "zone_id": null
  },
  "status": "warning",
  "summary": "Most greenhouses are stable, but greenhouse 2 zone 1 needs attention.",
  "observations": [
    "Greenhouse 1: temperature and soil moisture are within profile ranges.",
    "Greenhouse 2 zone 1: soil moisture dropped to 21%.",
    "Greenhouse 3: CO2 was elevated during the morning period."
  ],
  "recommendations": [
    "Review the tomato zone in greenhouse 2.",
    "Consider short watering for greenhouse 2 zone 1."
  ],
  "proposed_actions": [
    {
      "group_id": "group-001",
      "greenhouse_id": "gh-002",
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

## Explainability

Every tool call is logged in `ai_tool_calls` with:
- tool name and arguments
- scope identifiers
- result
- status and errors
- timestamp

UI shows which tools were used for each AI response:

```text
AI used:
- get_group_overview
- get_today_group_summary
- get_active_alerts
- compare_greenhouses
- search_plant_knowledge
```

## Code Structure

```text
app/services/ai_agent/
  agent.py
  openrouter_provider.py
  prompts.py
  tools/
    group_tools.py
    greenhouse_tools.py
    zone_tools.py
    telemetry_tools.py
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
