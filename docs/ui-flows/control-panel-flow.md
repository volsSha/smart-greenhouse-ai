# Control Panel Flow

The control page is implemented in `app/ui/pages/control.py`. It is the operator workspace for selecting a greenhouse zone, proposing actuator changes, and approving or rejecting commands.

## Page Load Flow

```text
Open /control
  -> GET /api/settings
     -> load persisted control_mode
  -> if control_mode = simulator
     -> GET /api/simulator/status
     -> mark proposals unavailable unless simulator is running
  -> GET /api/groups
     -> if no groups exist: enter local demo mode
     -> else select group
        -> GET /api/groups/{group_id}/greenhouses
        -> select greenhouse
           -> GET /api/groups/{group_id}/greenhouses/{greenhouse_id}/zones
           -> GET /api/groups/{group_id}/telemetry/latest
           -> GET /api/groups/{group_id}/plant-batches
           -> GET /api/commands/groups/{group_id}/recent
           -> build zone context and command lists
```

## Operator Selection Flow

```text
User selects group
  -> greenhouse list refreshes
  -> first available greenhouse is selected
  -> zones, telemetry, plants, and recent commands refresh

User selects greenhouse
  -> zones refresh
  -> map model rebuilds
  -> selected zone drawer resets until user clicks a zone

User clicks SVG zone or fallback zone button
  -> selected zone ID updates
  -> drawer opens with telemetry, plant context, pending proposals, and actuator controls
```

## Zone Map Diagram

```text
Greenhouse map
  -> Zone card status
     -> normal: latest telemetry within expected range
     -> warning: telemetry or pending command state needs attention
     -> pending badge: proposed/validated commands exist for zone
  -> click zone
     -> ZoneControlDrawer
        -> latest metric badges
        -> plant batch context
        -> pending proposed action cards
        -> actuator controls
```

## Actuator Proposal Flow

```text
In selected zone drawer
  -> user chooses actuator type
     -> pump | fan | heater | lamp
  -> user chooses supported action
     -> turn_on | turn_off | set_power | set_speed
  -> user adjusts duration/power/speed when action needs parameters
  -> click proposal button
     -> POST /api/commands/propose
        -> payload includes group_id, greenhouse_id, zone_id, actuator_id, actuator_type, action, mode
        -> backend validates safety and persisted control mode
        -> command status becomes proposed or validated
     -> page refreshes pending proposals
```

## Approval Flow

```text
Pending proposed action card
  -> Approve and Execute
     -> POST /api/commands/{id}/approve
        -> backend revalidates safety
        -> if mode = simulator
           -> simulator mode router applies command to zone state
        -> if mode = mqtt
           -> MQTT command publisher publishes scoped command topic
        -> command moves to recent outcomes
  -> Reject
     -> POST /api/commands/{id}/cancel
        -> command becomes cancelled/rejected
        -> pending badge disappears after refresh
```

## Demo Mode Flow

```text
No persisted groups found
  -> /control renders hardcoded demo zones and telemetry
  -> proposal/approval/rejection actions update local page state
  -> no command API execution is required for demo interactions
```

## Refresh and Polling

```text
User clicks Refresh
  -> reload control mode
  -> reload simulator status when needed
  -> reload groups/greenhouses/zones/telemetry/plants/commands

Every 10 seconds
  -> GET /api/commands/groups/{group_id}/recent
  -> update pending and recent command sections
```

## Related Files

- `app/ui/pages/control.py`
- `app/ui/components/greenhouse_map.py`
- `app/ui/components/zone_control_drawer.py`
- `app/ui/components/actuator_controls.py`
- `app/ui/components/proposed_action_card.py`
- `app/ui/components/control_panel_state.py`
- `app/api/commands.py`
- `app/services/simulator/mode_router.py`