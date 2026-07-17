"""Database infrastructure for IELTS AI Coach."""

from ielts_ai_coach.database.connection import initialize_database
from ielts_ai_coach.database.models import User

__all__ = ["User", "initialize_database"]
