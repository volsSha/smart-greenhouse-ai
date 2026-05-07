# Testing

Run the full automated suite:

```bash
uv run pytest
```

## Test tiers

- `tests/unit`: pure schemas, services, view models, rules, and validation logic.
- `tests/integration`: API routes, repositories, command lifecycle, RAG search, and service orchestration with fakes where external systems are unavailable.
- `tests/system`: end-to-end invariants across MQTT topic construction, telemetry ingestion, alerts, AI grounding, RAG, command approval, and safety boundaries.

## Demo gates

1. Phase 1: simulator telemetry reaches ingestion and dashboard query paths.
2. Phase 2: plant profile threshold breaches create visible alerts.
3. Phase 3: AI chat answers with scoped read-only tools and RAG citations when available.
4. Phase 4: proposed actuator actions require approval and publish exactly once after validation.

## Safety regression checks

The suite includes negative system tests proving AI tools and control-engine rules cannot publish MQTT commands directly. Any future autonomous actuation mode needs a separate security plan and new tests.
