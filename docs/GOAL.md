# Smart Greenhouse AI - Project Goal

## What

An explainable AI-IoT control system for a small greenhouse that combines sensor telemetry, rule-based control, LLM reasoning, and RAG knowledge to help users monitor and manage their plants through natural language.

## Why

Most greenhouse systems either:
- Are purely automation (no intelligence, no explanations)
- Are simple dashboards (no reasoning, no recommendations)
- Have AI that hallucinates (no grounding in real data)

This system bridges the gap: AI that reasons over **actual** sensor data, knows plant-specific thresholds, searches domain knowledge, and proposes actions through a safety-validated pipeline.

## Key Differentiator

**AI does not fabricate answers.** Every claim is backed by:
- Real telemetry from InfluxDB
- Plant profiles from PostgreSQL
- Historical command data
- RAG-sourced agronomic knowledge
- Active alerts

All tool calls are logged and visible to the user.

## Scientific Value

Demonstrates:
- Cyber-physical architecture
- Event-driven MQTT communication
- Time-series analysis
- Rule-based / PID / Fuzzy control
- LLM tool usage
- RAG for domain knowledge
- Safety validation
- Audit logging
- Physical environment simulation

## Practical Value

Users can ask:
- "How are my plants?"
- "Why is humidity dropping?"
- "Should I water today?"
- "What happened with temperature last night?"
- "Explain the last alert."
- "Suggest a regime for tomatoes."

And get answers grounded in real data, not hallucinations.

## Academic Formulation

> The work proposes an extended Python-oriented monorepo architecture for an intelligent small greenhouse control system. The architecture combines MQTT broker Mosquitto for event-based telemetry exchange, FastAPI as the central backend, NiceGUI as the web interface for monitoring and control, InfluxDB for sensor time-series storage, PostgreSQL for structured system data, pgvector for RAG-based domain knowledge retrieval, and an OpenRouter-based LLM Agent for natural language interaction.
>
> The intelligent agent has no direct access to actuators. It uses tool calling to retrieve factual data, analyzes plant state, generates explanations, and creates structured control intents. All potential actions pass through backend-level validation and safety rules, after which they can be confirmed by the user and sent to the MQTT broker as actuator commands.
