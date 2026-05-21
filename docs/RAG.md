# RAG - Retrieval Augmented Generation

## Purpose

RAG provides the AI agent with domain-specific agronomic and system knowledge for a **group of greenhouses**. It is not for generic document chat. It helps the AI combine knowledge with real-time group, greenhouse, and zone telemetry.

## What to Store

- Care rules for tomato, cucumber, pepper, lettuce, etc.
- Symptoms of water deficiency, overheating, nutrient deficiency
- Optimal parameters for different growth stages
- Greenhouse-zone management practices
- CO2 interpretation guidelines
- Group and zone-level safety rules
- System documentation and actuator constraints
- User's own notes and observations scoped to a group or greenhouse

## How It Works

```text
User asks: "Why might leaves be wilting in greenhouse 2 zone 1?"

1. AI calls: get_zone_state(group_id="group-001", greenhouse_id="gh-002", zone_id="zone-01")
2. AI calls: get_today_zone_summary(group_id="group-001", greenhouse_id="gh-002", zone_id="zone-01")
3. AI calls: search_plant_knowledge(query="wilting leaves, low soil moisture, tomatoes", group_id="group-001")
4. RAG returns matches with title, source, content, and score
5. AI combines:
   - RAG knowledge
   - zone telemetry from InfluxDB
   - plant batch and profile from PostgreSQL
   - active alerts
6. AI responds with scoped, data-grounded explanation
```

## Database

- `rag_documents` - source documents with optional `group_id`
- `rag_chunks` - chunked text with embeddings, metadata, and embedding model

## Embedding Model

Default dimension: 1536 for OpenAI-compatible embeddings. Resolve the embedding provider before the initial migration. If using local `sentence-transformers`, update the vector dimension before creating data.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rag/documents` | Add curated document to knowledge base |
| POST | `/api/rag/reindex` | Rebuild all embeddings |
| GET | `/api/rag/search` | Semantic search with optional group scope |

## AI Tool

```text
search_plant_knowledge(query: str, group_id: str | None = None)
```

The tool must return source attribution so the UI and AI response can show where agronomic advice came from.

## Ukrainian Flow References

Upload-ready Ukrainian RAG documentation is included in:

- `docs/llm-upload-uk/03-operational-flows-uk.md` — RAG ingestion and scoped AI usage flow.
- `docs/llm-upload-uk/04-examples-and-payloads-uk.md` — example AI response combining telemetry, plant profile, alerts, and RAG.
- `docs/llm-upload-uk/ALL-IN-ONE-uk.md` — combined LLM upload file.
