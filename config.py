"""Application-wide configuration for AI Study Coach."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "study_coach.db"

APP_TITLE = "AI Study Coach"
APP_SUBTITLE = "你的雅思备考小教练"

SUBJECTS = ("listening", "reading", "writing", "speaking")
SUBJECT_LABELS = {
    "listening": "听力",
    "reading": "阅读",
    "writing": "写作",
    "speaking": "口语",
}
