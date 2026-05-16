# AI Chat Flow

The AI chat page is implemented in `app/ui/pages/ai_chat.py`. It combines scoped conversation history, read-only tool use, and proposed action approval cards.

## Conversation Load Flow

```text
Open /ai-chat
  -> GET /api/ai/conversations
  -> render conversation selector
  -> user chooses existing conversation
     -> GET /api/ai/conversations/{conversation_id}
     -> render messages
     -> restore saved group/greenhouse/zone scope
     -> GET /api/ai/tool-calls/{conversation_id}
     -> attach tool traces to assistant messages
```

## Scope Selection Flow

```text
New or existing conversation
  -> GET /api/groups
  -> user selects group, or keeps fleet-wide scope
     -> GET /api/groups/{group_id}/greenhouses
     -> user selects greenhouse, or keeps group scope
        -> GET /api/groups/{group_id}/greenhouses/{greenhouse_id}/zones
        -> user selects zone, or keeps greenhouse scope

Clear scope
  -> group_id, greenhouse_id, and zone_id reset
  -> next AI message is fleet-wide
```

## Send Message Flow

```text
User types message
  -> Send
     -> POST /api/ai/chat
        -> includes conversation_id when continuing
        -> includes selected group_id / greenhouse_id / zone_id when scoped
        -> AI agent calls read-only tools as needed
        -> AI returns structured observations, recommendations, and optional proposed actions
     -> UI appends user and assistant messages
     -> UI renders tool-call trace panels
     -> UI renders proposed action cards when commands were created
```

## Proposed Action Flow in Chat

```text
Assistant response contains proposed action
  -> ProposedActionCard renders status, scope, actuator, action, and mode
  -> user clicks Approve and Execute
     -> POST /api/commands/{id}/approve
     -> card refreshes with executed/failed status
  -> user clicks Reject
     -> POST /api/commands/{id}/cancel
     -> card refreshes with cancelled status
```

## Retry Flow

```text
POST /api/ai/chat fails
  -> error message renders with Retry
  -> user clicks Retry
     -> same message and scope are submitted again
```

## Safety Boundary

```text
AI chat
  -> may read telemetry, logs, RAG, and registry context through tools
  -> may create proposed actions
  -> must not publish MQTT or mutate actuators directly
  -> operator approval and backend safety validation are required before execution
```

## Related Files

- `app/ui/pages/ai_chat.py`
- `app/ui/components/chat_message.py`
- `app/ui/components/proposed_action_card.py`
- `app/ui/components/tool_call_trace.py`
- `app/api/ai_chat.py`
- `app/api/commands.py`
- `docs/AI_AGENT.md`