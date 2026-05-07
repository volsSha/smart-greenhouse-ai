"""Session helper for repository layer.

Provides get_session as a convenience re-export from dependencies.
"""

from app.dependencies import get_db_session as get_session
