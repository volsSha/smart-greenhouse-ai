# RAG - Retrieval Augmented Generation

## Purpose

RAG provides the AI agent with domain-specific agronomic knowledge. It is not for "chatting with PDFs" - it is for practical agricultural context that the AI combines with real-time telemetry data.

## What to Store

- Care rules for tomato, cucumber, pepper, lettuce, etc.
- Symptoms of water deficiency, overheating, nutrient deficiency
- Optimal parameters for different growth stages (seedling, vegetative, flowering, fruiting)
- CO2 interpretation guidelines
- System documentation and actuator safety rules
- User's own notes and observations

## How It Works

```
User asks: "Why might leaves be wilting?"

1. AI calls: search_plant_knowledge(query="wilting leaves, low soil moisture, tomatoes")
2. RAG returns:
   {
     "matches": [
       {
         "title": "Tomatoes: Water Deficiency",
         "content": "Wilting can be caused by low soil moisture...",
         "score": 0.82
       }
     ]
   }
3. AI combines:
   - RAG knowledge
   - Today's telemetry from InfluxDB
   - Plant profile from PostgreSQL
4. AI responds with context-grounded answer
```

## Database

- `rag_documents` - source documents (title, content, metadata)
- `rag_chunks` - chunked text with embeddings (pgvector)

## Embedding Model

Default dimension: 1536 (OpenAI text-embedding-3-small). Adjust if using a different model.

## API

| Method | Endpoint            | Description                    |
|--------|---------------------|--------------------------------|
| POST   | `/api/rag/documents`| Add document to knowledge base |
| POST   | `/api/rag/reindex`  | Rebuild all embeddings         |
| GET    | `/api/rag/search`   | Semantic search                |
