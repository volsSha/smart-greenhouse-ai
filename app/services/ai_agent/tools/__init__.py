"""Read-only AI tools for the Smart Greenhouse agent."""

from app.services.ai_agent.tools.alert_tools import get_active_alerts
from app.services.ai_agent.tools.command_tools import get_recent_commands
from app.services.ai_agent.tools.greenhouse_tools import (
    compare_greenhouses,
    get_greenhouse_list,
    get_greenhouse_state,
)
from app.services.ai_agent.tools.group_tools import get_group_overview
from app.services.ai_agent.tools.plant_tools import get_plant_batches, get_plant_profile
from app.services.ai_agent.tools.rag_tools import search_plant_knowledge
from app.services.ai_agent.tools.telemetry_tools import (
    get_latest_readings,
    get_today_greenhouse_summary,
    get_today_group_summary,
    get_today_zone_summary,
)
from app.services.ai_agent.tools.zone_tools import get_zone_plant_info, get_zone_state
from app.services.ai_agent.tools.deps import ToolDeps

ALL_TOOLS = [
    get_group_overview,
    get_greenhouse_list,
    get_greenhouse_state,
    compare_greenhouses,
    get_zone_state,
    get_zone_plant_info,
    get_plant_batches,
    get_plant_profile,
    get_today_group_summary,
    get_today_greenhouse_summary,
    get_today_zone_summary,
    get_latest_readings,
    get_active_alerts,
    get_recent_commands,
    search_plant_knowledge,
]

__all__ = [
    "ALL_TOOLS",
    "ToolDeps",
    "get_group_overview",
    "get_greenhouse_list",
    "get_greenhouse_state",
    "compare_greenhouses",
    "get_zone_state",
    "get_zone_plant_info",
    "get_plant_batches",
    "get_plant_profile",
    "get_today_group_summary",
    "get_today_greenhouse_summary",
    "get_today_zone_summary",
    "get_latest_readings",
    "get_active_alerts",
    "get_recent_commands",
    "search_plant_knowledge",
]
