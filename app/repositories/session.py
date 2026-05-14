"""Session helper for repository layer."""

from app.dependencies import get_db_session as get_session

__all__ = ["get_session"]
