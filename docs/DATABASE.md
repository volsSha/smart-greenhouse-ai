# Database Schema

## Overview

Two databases with distinct roles:
- **InfluxDB** - high-frequency sensor telemetry (time-series)
- **PostgreSQL + pgvector** - structured business data, AI logs, RAG embeddings

---

## PostgreSQL Tables

### greenhouses

```sql
CREATE TABLE greenhouses (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### plants

```sql
CREATE TABLE plants (
    id UUID PRIMARY KEY,
    greenhouse_id UUID NOT NULL REFERENCES greenhouses(id),
    name TEXT NOT NULL,
    species TEXT,
    cultivar TEXT,
    planted_at DATE,
    growth_stage TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### plant_profiles

Critical table - gives AI context about what conditions are normal for each plant.

```sql
CREATE TABLE plant_profiles (
    id UUID PRIMARY KEY,
    crop_name TEXT NOT NULL,
    growth_stage TEXT,
    temp_min REAL,
    temp_opt REAL,
    temp_max REAL,
    humidity_min REAL,
    humidity_opt REAL,
    humidity_max REAL,
    soil_moisture_min REAL,
    soil_moisture_opt REAL,
    soil_moisture_max REAL,
    co2_min REAL,
    co2_opt REAL,
    co2_max REAL,
    light_min REAL,
    light_opt REAL,
    light_max REAL,
    description TEXT
);
```

### control_setpoints

```sql
CREATE TABLE control_setpoints (
    id UUID PRIMARY KEY,
    greenhouse_id UUID NOT NULL REFERENCES greenhouses(id),
    temperature_target REAL,
    humidity_target REAL,
    soil_moisture_target REAL,
    co2_target REAL,
    light_target REAL,
    updated_by TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### command_log

```sql
CREATE TABLE command_log (
    id UUID PRIMARY KEY,
    greenhouse_id UUID NOT NULL REFERENCES greenhouses(id),
    actuator TEXT NOT NULL,
    action TEXT NOT NULL,
    value REAL,
    unit TEXT,
    source TEXT NOT NULL,   -- manual | control_engine | ai_agent | grafana_alert | safety_override
    reason TEXT,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### ai_conversations

```sql
CREATE TABLE ai_conversations (
    id UUID PRIMARY KEY,
    greenhouse_id UUID REFERENCES greenhouses(id),
    user_id UUID,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### ai_messages

```sql
CREATE TABLE ai_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model TEXT,
    token_input INTEGER,
    token_output INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### ai_tool_calls

For explainability - every tool invocation is logged.

```sql
CREATE TABLE ai_tool_calls (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id),
    tool_name TEXT NOT NULL,
    arguments JSONB NOT NULL,
    result JSONB,
    status TEXT NOT NULL,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### rag_documents

```sql
CREATE TABLE rag_documents (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    source_type TEXT,
    source_url TEXT,
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### rag_chunks

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE rag_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES rag_documents(id),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

> Embedding dimension (1536) depends on the embedding model. Adjust if using a different model.

---

## InfluxDB Measurements

### greenhouse_telemetry

```
tags:   greenhouse_id, sensor_id, metric
fields: value (float), quality (string)
time:   timestamp
```

Metrics stored: temperature, air_humidity, co2, light, soil_moisture, fan_power, pump_state, heater_power, lamp_state.
