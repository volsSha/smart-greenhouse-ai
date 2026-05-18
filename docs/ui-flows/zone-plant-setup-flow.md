# Zone and Plant Setup Flow

The zones page is implemented in `app/ui/pages/zone_management.py`. It prepares the registry data used by MQTT telemetry, dashboard views, control proposals, and AI chat scope.

## Scope Load Flow

```text
Open /zones
  -> GET /api/groups
  -> user selects group
     -> GET /api/groups/{group_id}/greenhouses
     -> user selects greenhouse
        -> GET /api/groups/{group_id}/greenhouses/{greenhouse_id}/zones
        -> GET /api/groups/{group_id}/devices/edge-nodes
        -> GET /api/groups/{group_id}/plant-batches
```

## Add Zone Flow

```text
User clicks Add zone
  -> form collects zone name/type/metadata
  -> POST /api/groups/{group_id}/greenhouses/{greenhouse_id}/zones
     -> zone is persisted
     -> page can create or display matching edge-node identity
     -> zone list refreshes
```

## MQTT Identity Flow

```text
Zone exists
  -> Show topic
     -> display telemetry topic
        -> greenhouse-groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}/telemetry
  -> operator copies group_id / greenhouse_id / zone_id / broker settings to firmware config
  -> Wokwi or physical device publishes telemetry to topic
  -> backend subscriber writes telemetry
  -> dashboard/control/AI chat can read scoped state
```

## Add Plant Batch Flow

```text
User clicks Add plants
  -> choose zone and plant metadata
  -> POST /api/groups/{group_id}/plant-batches
  -> plant batch appears in zone context
  -> /control drawer shows plant context for selected zone
  -> AI chat tools can use plant context in recommendations
```

## Delete Zone Flow

```text
User clicks Delete on zone
  -> DELETE /api/groups/{group_id}/greenhouses/{greenhouse_id}/zones/{zone_id}
  -> page refreshes zones
  -> scope selectors on /control and /ai-chat no longer show deleted zone
```

## Firmware Setup Flow

```text
/zones Wokwi / MQTT Setup section
  -> create or select group/greenhouse/zone
  -> copy IDs and topic into firmware config
  -> run Wokwi MicroPython device
  -> device publishes telemetry
  -> /simulator MQTT panel confirms broker connectivity
  -> /dashboard and /control show telemetry for the registered scope
```

## Related Files

- `app/ui/pages/zone_management.py`
- `app/api/greenhouses.py`
- `app/api/devices.py`
- `app/api/plants.py`
- `docs/wokwi-mqtt-mode.md`
- `firmware/wokwi-greenhouse-zone/README.md`