# Smart Greenhouse Management System - Project Goal

## What

An intelligent cyber-physical system for monitoring and controlling the microclimate of a group of small greenhouses. The system combines IoT telemetry, MQTT communication, time-series analytics, structured greenhouse metadata, rule-based safety validation, LLM reasoning, and RAG knowledge to help users manage multiple greenhouse objects through dashboards and natural language.

Academic formulation:

> Intelligent cyber-physical system for monitoring and controlling the microclimate of a group of greenhouses using IoT, MQTT, time-series analytics, and an LLM interface.

Short Ukrainian formulation:

> Кіберфізична система керування групою теплиць.

Full Ukrainian formulation:

> Інтелектуальна кіберфізична система моніторингу та керування мікрокліматом групи теплиць із використанням IoT, MQTT, time-series аналітики та LLM-інтерфейсу.

## Why

Most greenhouse systems either:
- monitor one greenhouse in isolation
- automate devices without explanations
- show dashboards without cross-greenhouse reasoning
- use AI that can hallucinate because it is not grounded in real telemetry

This system bridges the gap for a small greenhouse fleet: it understands greenhouse groups, individual greenhouses, zones, sensors, actuators, plants, alerts, command history, and agronomic knowledge. The AI can analyze one zone, one greenhouse, or the whole group and explain where attention is needed.

## Key Differentiator

**AI does not fabricate answers and does not directly control actuators.** Every claim is backed by:
- real telemetry from InfluxDB scoped by group, greenhouse, zone, sensor, and metric
- greenhouse, zone, plant batch, sensor, and actuator metadata from PostgreSQL
- plant profiles and control policies
- historical command data
- RAG-sourced agronomic knowledge
- active alerts at zone, greenhouse, and group level

All tool calls are logged and visible to the user. All physical actions are proposed as structured commands and pass through backend safety validation and user approval before MQTT execution.

## Domain Model

```text
GreenhouseGroup
  ├── Greenhouse
  │   ├── GreenhouseZone
  │   │   ├── Sensor
  │   │   ├── Actuator
  │   │   ├── PlantBatch
  │   │   └── ControlSetpoint
  │   ├── EdgeNode
  │   ├── Alert
  │   ├── Command
  │   └── Telemetry
  └── GroupPolicy
```

The primary domain entity is `GreenhouseGroup`, not a single greenhouse. A group contains multiple greenhouses, each greenhouse contains zones, and each zone owns its sensor, actuator, plant, setpoint, alert, and telemetry context.

## Scientific Value

Demonstrates:
- multi-greenhouse cyber-physical architecture
- event-driven MQTT communication with scoped topics
- fleet and zone-level time-series analysis
- rule-based safety validation
- LLM tool usage across group, greenhouse, and zone contexts
- RAG for agronomic knowledge
- command approval and audit logging
- physical environment simulation with multiple edge nodes
- aggregated group-level state and problem prioritization

## Practical Value

Users can ask:
- "How are my greenhouses?"
- "Which greenhouse has problems today?"
- "How are the tomatoes in greenhouse 2, zone 1?"
- "Compare greenhouse 1 and greenhouse 2."
- "Why did soil moisture drop in zone 2?"
- "Should I water the tomato zone today?"
- "What happened with temperature last night across the group?"
- "Prioritize active alerts across all greenhouses."

And get answers grounded in real group, greenhouse, and zone data rather than hallucinations.
