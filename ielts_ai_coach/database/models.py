"""Stable public exports for every active SQLAlchemy model."""

from ielts_ai_coach.database.base import Base as Base
from ielts_ai_coach.database.account_models import (
    ScoreRecord as ScoreRecord,
    StudentProfile as StudentProfile,
    User as User,
)
from ielts_ai_coach.database.ai_models import (
    AIUsageDaily as AIUsageDaily,
    CoachMessage as CoachMessage,
    Essay as Essay,
    WritingFeedback as WritingFeedback,
)
from ielts_ai_coach.database.exercise_models import (
    TaskQuestionAttempt as TaskQuestionAttempt,
)
from ielts_ai_coach.database.plan_models import (
    PlanTask as PlanTask,
    StudyLog as StudyLog,
    StudyPlan as StudyPlan,
)

__all__ = [
    "AIUsageDaily",
    "Base",
    "CoachMessage",
    "Essay",
    "PlanTask",
    "ScoreRecord",
    "StudentProfile",
    "StudyLog",
    "StudyPlan",
    "TaskQuestionAttempt",
    "User",
    "WritingFeedback",
]
