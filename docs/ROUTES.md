# API Routes and MQTT Topics

## Greenhouse Groups

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/groups` | List greenhouse groups |
| POST | `/api/groups` | Create greenhouse group |
| GET | `/api/groups/{group_id}` | Get group details and aggregate state |
| PATCH | `/api/groups/{group_id}` | Update group metadata |

## Greenhouses and Zones

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/groups/{group_id}/greenhouses` | List greenhouses in a group |
| POST | `/api/groups/{group_id}/greenhouses` | Create greenhouse |
| GET | `/api/groups/{group_id}/greenhouses/{greenhouse_id}` | Get greenhouse details |
| PATCH | `/api/groups/{group_id}/greenhouses/{greenhouse_id}` | Update greenhouse |
| GET | `/api/groups/{group_id}/greenhouses/{greenhouse_id}/zones` | List greenhouse zones |
| POST | `/api/groups/{group_id}/greenhouses/{greenhouse_id}/zones` | Create zone |
| GET | `/api/groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}` | Get zone details |
| PATCH | `/api/groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}` | Update zone |

## Device Registry

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/groups/{group_id}/devices/edge-nodes` | List edge nodes |
| POST | `/api/groups/{group_id}/devices/edge-nodes` | Register edge node |
| GET | `/api/groups/{group_id}/devices/sensors` | List sensors |
| POST | `/api/groups/{group_id}/devices/sensors` | Register sensor |
| GET | `/api/groups/{group_id}/devices/actuators` | List actuators |
| POST | `/api/groups/{group_id}/devices/actuators` | Register actuator |

## Telemetry

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/groups/{group_id}/telemetry/latest` | Latest readings across the group |
| GET | `/api/groups/{group_id}/telemetry/summary/today` | Today's group aggregate summary |
| GET | `/api/groups/{group_id}/greenhouses/{greenhouse_id}/telemetry/summary/today` | Today's greenhouse summary |
| GET | `/api/groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/telemetry/summary/today` | Today's zone summary |
| GET | `/api/groups/{group_id}/telemetry/range` | Historical telemetry range filtered by greenhouse/zone/metric |
| GET | `/api/groups/{group_id}/telemetry/anomalies` | Group, greenhouse, or zone anomalies |
| GET | `/api/groups/{group_id}/compare-greenhouses` | Compare greenhouse microclimate summaries |

## Plants

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/groups/{group_id}/plant-batches` | List plant batches |
| POST | `/api/groups/{group_id}/plant-batches` | Create plant batch |
| GET | `/api/groups/{group_id}/plant-batches/{batch_id}` | Get plant batch details |
| PATCH | `/api/groups/{group_id}/plant-batches/{batch_id}` | Update plant batch |
| GET | `/api/plant-profiles` | List reusable plant profiles |
| POST | `/api/plant-profiles` | Create plant profile |

## AI Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ai/chat` | Send message to AI agent with optional group/greenhouse/zone scope |
| GET | `/api/ai/conversations` | List conversations |
| GET | `/api/ai/conversations/{id}` | Get conversation with messages |
| GET | `/api/ai/tool-calls/{conv_id}` | Get tool calls for conversation |

## Commands

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/commands/propose` | Propose a scoped control command |
| POST | `/api/commands/{id}/approve` | Approve proposed command |
| POST | `/api/commands/{id}/cancel` | Cancel proposed command |
| GET | `/api/groups/{group_id}/commands/recent` | Recent command history filtered by greenhouse/zone |

## RAG

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rag/documents` | Add curated document to knowledge base |
| POST | `/api/rag/reindex` | Rebuild embeddings |
| GET | `/api/rag/search` | Semantic search in knowledge base |

## Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get current model settings, embedding config, catalog refresh status, and persisted control mode |
| PUT | `/api/settings` | Update selected chat model (must exist in catalog) |
| PUT | `/api/settings/control-mode` | Update persisted command execution mode (`mqtt` or `simulator`) |
| GET | `/api/settings/catalog` | List OpenRouter model catalog with optional search/provider/capability filters |
| POST | `/api/settings/catalog/refresh` | Refresh catalog from OpenRouter API |

## Simulator and MQTT Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/simulator/status` | Get internal simulator runtime status and active configuration |
| POST | `/api/simulator/start` | Start internal simulator with scenario, topology, and interval config |
| POST | `/api/simulator/stop` | Stop internal simulator runtime |
| GET | `/api/simulator/zones` | Get live simulator zone state for UI visualization |
| GET | `/api/mqtt/status` | Get MQTT broker/client status for Wokwi or remote-device operation |

## NiceGUI Pages

`/` redirects to `/dashboard`. NiceGUI pages are registered by importing page modules before `ui.run_with(app, ...)`; see `docs/solutions/ui-bugs/docker-compose-fastapi-nicegui-dashboard-launch-fix-2026-05-07.md` for the dashboard launch fix. Detailed page and button flows live in `docs/ui-flows/README.md`.

| Page | Description |
|------|-------------|
| `/dashboard` | Fleet telemetry overview, greenhouse cards, zone drill-down charts, and anomaly alerts |
| `/simulator` | Internal simulator controls, scenario selection, live zone visualization, and MQTT status display |
| `/zones` | Group/greenhouse zone setup, edge-node identity, MQTT topic display, and plant batch creation |
| `/plants` | Planned plant-profile and plant-batch workspace |
| `/control` | Operator panel with greenhouse map, zone drawer, actuator proposals, approvals, and recent outcomes |
| `/ai-chat` | Scoped AI conversation with tool transparency and proposed action approval cards |
| `/logs` | Persisted debug logs with level/component/event filters and expandable failure details |
| `/rag` | Knowledge-base documents, upload, reindex, and semantic search |
| `/settings` | Model catalog, selected AI model, embedding config, and persisted control mode |

## MQTT Topics

### Readable Topic Form

```text
greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/telemetry
greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/commands
greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/alerts
greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/state
```

### Short Practical Topic Form

```text
gh/{group_id}/{greenhouse_id}/{zone_id}/telemetry
gh/{group_id}/{greenhouse_id}/{zone_id}/commands
gh/{group_id}/{greenhouse_id}/{zone_id}/alerts
gh/{group_id}/{greenhouse_id}/{zone_id}/state
```

Use the readable topic form as the canonical default. The short form can be added later as an alias if payload size or operational convenience matters.

### Examples

```text
greenhouse-groups/group-001/greenhouses/gh-001/zones/zone-01/telemetry
greenhouse-groups/group-001/greenhouses/gh-002/zones/zone-01/telemetry
greenhouse-groups/group-001/greenhouses/gh-002/zones/zone-02/commands
```
