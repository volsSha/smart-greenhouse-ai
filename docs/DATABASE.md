# Database Schema

## Overview

Two databases with distinct roles:
- **InfluxDB** - high-frequency microclimate telemetry across greenhouse groups, greenhouses, zones, sensors, and metrics
- **PostgreSQL + pgvector** - structured fleet data, device registry, plant batches, policies, commands, AI logs, and RAG embeddings

---

## PostgreSQL Tables

### greenhouse_groups

```sql
CREATE TABLE greenhouse_groups (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### greenhouses

```sql
CREATE TABLE greenhouses (
    id UUID PRIMARY KEY,
    group_id UUID NOT NULL REFERENCES greenhouse_groups(id),
    name TEXT NOT NULL,
    location TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### greenhouse_zones

```sql
CREATE TABLE greenhouse_zones (
    id UUID PRIMARY KEY,
    greenhouse_id UUID NOT NULL REFERENCES greenhouses(id),
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### edge_nodes

```sql
CREATE TABLE edge_nodes (
    id UUID PRIMARY KEY,
    greenhouse_id UUID NOT NULL REFERENCES greenhouses(id),
    node_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    node_type TEXT NOT NULL, -- esp32 | simulator | gateway
    firmware_version TEXT,
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### sensor_registry

```sql
CREATE TABLE sensor_registry (
    id UUID PRIMARY KEY,
    zone_id UUID NOT NULL REFERENCES greenhouse_zones(id),
    edge_node_id UUID REFERENCES edge_nodes(id),
    sensor_key TEXT NOT NULL,
    metric TEXT NOT NULL,
    unit TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(zone_id, sensor_key)
);
```

### actuator_registry

```sql
CREATE TABLE actuator_registry (
    id UUID PRIMARY KEY,
    zone_id UUID NOT NULL REFERENCES greenhouse_zones(id),
    edge_node_id UUID REFERENCES edge_nodes(id),
    actuator_key TEXT NOT NULL,
    actuator_type TEXT NOT NULL, -- pump | fan | heater | lamp
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(zone_id, actuator_key)
);
```

### plant_batches

```sql
CREATE TABLE plant_batches (
    id UUID PRIMARY KEY,
    zone_id UUID NOT NULL REFERENCES greenhouse_zones(id),
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

Critical table - gives AI and rules context about what conditions are normal for each crop/growth stage.

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

### group_control_policies

```sql
CREATE TABLE group_control_policies (
    id UUID PRIMARY KEY,
    group_id UUID NOT NULL REFERENCES greenhouse_groups(id),
    name TEXT NOT NULL,
    policy JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### control_setpoints

```sql
CREATE TABLE control_setpoints (
    id UUID PRIMARY KEY,
    zone_id UUID NOT NULL REFERENCES greenhouse_zones(id),
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
    group_id UUID NOT NULL REFERENCES greenhouse_groups(id),
    greenhouse_id UUID NOT NULL REFERENCES greenhouses(id),
    zone_id UUID NOT NULL REFERENCES greenhouse_zones(id),
    actuator_id UUID REFERENCES actuator_registry(id),
    actuator TEXT NOT NULL,
    action TEXT NOT NULL,
    value REAL,
    unit TEXT,
    duration_seconds INTEGER,
    source TEXT NOT NULL, -- manual | control_engine | ai_agent | safety_override
    reason TEXT,
    validation_errors JSONB,
    status TEXT NOT NULL, -- proposed | validated | approved | executing | executed | cancelled | rejected | expired | failed
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### alert_log

```sql
CREATE TABLE alert_log (
    id UUID PRIMARY KEY,
    group_id UUID NOT NULL REFERENCES greenhouse_groups(id),
    greenhouse_id UUID REFERENCES greenhouses(id),
    zone_id UUID REFERENCES greenhouse_zones(id),
    metric TEXT,
    severity TEXT NOT NULL, -- info | warning | critical
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL, -- active | resolved | dismissed
    source TEXT NOT NULL, -- threshold | control_engine | ai_agent | system
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);
```

### ai_conversations

```sql
CREATE TABLE ai_conversations (
    id UUID PRIMARY KEY,
    group_id UUID REFERENCES greenhouse_groups(id),
    greenhouse_id UUID REFERENCES greenhouses(id),
    zone_id UUID REFERENCES greenhouse_zones(id),
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
    group_id UUID REFERENCES greenhouse_groups(id),
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
    embedding_model TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

> Embedding dimension (1536) depends on the embedding model. Resolve the embedding provider before the first migration or change the vector dimension intentionally before data exists.

---

## InfluxDB Measurements

### microclimate

```text
tags:   group_id, greenhouse_id, zone_id, sensor_id, metric
fields: value (float), quality (string)
time:   timestamp
```

Metrics stored: temperature, air_humidity, co2, light, soil_moisture, fan_power, pump_state, heater_power, lamp_state.

Example point:

```json
{
  "measurement": "microclimate",
  "tags": {
    "group_id": "group-001",
    "greenhouse_id": "gh-002",
    "zone_id": "zone-01",
    "sensor_id": "soil-01",
    "metric": "soil_moisture"
  },
  "fields": {
    "value": 24.5,
    "quality": "ok"
  }
}
```
