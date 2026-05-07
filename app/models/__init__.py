"""Import all ORM models so Alembic can autogenerate migrations."""

from app.models.alert import Alert
from app.models.ai import AIConversation, AIMessage, AIToolCall
from app.models.base import Base
from app.models.command import CommandLog
from app.models.device import Actuator, EdgeNode, Sensor
from app.models.greenhouse import Greenhouse
from app.models.group import GreenhouseGroup
from app.models.plant_batch import ControlSetpoint, GroupControlPolicy, PlantBatch, PlantProfile
from app.models.rag import RAGChunk, RAGDocument
from app.models.zone import GreenhouseZone

__all__ = [
    "Base",
    "Alert",
    "AIConversation",
    "AIMessage",
    "AIToolCall",
    "CommandLog",
    "Actuator",
    "EdgeNode",
    "Sensor",
    "Greenhouse",
    "GreenhouseGroup",
    "ControlSetpoint",
    "GroupControlPolicy",
    "PlantBatch",
    "PlantProfile",
    "RAGChunk",
    "RAGDocument",
    "GreenhouseZone",
]
