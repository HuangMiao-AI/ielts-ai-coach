"""Runtime configuration for IELTS AI Coach."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import make_url


APP_TITLE = "IELTS AI Coach"
APP_SUBTITLE = "你的智能雅思学习助手"
SUPPORTED_PYTHON = (3, 12)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "ielts_ai_coach.db"
BACKUP_DIR = DATA_DIR / "backups"
DEFAULT_DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"
DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


@dataclass(frozen=True)
class AISettings:
    """Validated configuration for the active AI provider."""

    api_key: str
    base_url: str
    model_name: str
    timeout_seconds: float
    max_retries: int


def ensure_supported_python(
    version: tuple[int, int] | None = None,
) -> None:
    """Raise an error when the runtime is not Python 3.12.x."""

    active_version = version or (sys.version_info.major, sys.version_info.minor)
    if active_version != SUPPORTED_PYTHON:
        raise RuntimeError(
            "IELTS AI Coach requires Python 3.12.x; "
            f"received Python {active_version[0]}.{active_version[1]}."
        )


def get_setting(name: str, default: str) -> str:
    """Read a setting from the environment or Streamlit secrets."""

    environment_value = os.getenv(name)
    if environment_value:
        return environment_value

    try:
        import streamlit as st

        secret_value = st.secrets.get(name)
    except Exception:
        secret_value = None

    return str(secret_value) if secret_value not in (None, "") else default


def get_database_url() -> str:
    """Return a stable SQLAlchemy URL for the active application database."""

    configured_url = get_setting("DATABASE_URL", DEFAULT_DATABASE_URL)
    parsed_url = make_url(configured_url)
    if not parsed_url.drivername.startswith("sqlite"):
        return configured_url
    if parsed_url.database in (None, "", ":memory:"):
        return configured_url

    database_path = Path(parsed_url.database).expanduser()
    if database_path.is_absolute():
        return configured_url
    resolved_path = (BASE_DIR / database_path).resolve().as_posix()
    return str(parsed_url.set(database=resolved_path))


def get_backup_dir() -> Path:
    """Return the configured SQLite backup directory."""

    return Path(get_setting("BACKUP_DIR", str(BACKUP_DIR))).expanduser().resolve()


def get_ai_settings() -> AISettings:
    """Return Qwen-compatible settings without exposing secret values."""

    api_key = get_setting(
        "QWEN_API_KEY",
        get_setting("DASHSCOPE_API_KEY", ""),
    ).strip()
    base_url = get_setting("QWEN_BASE_URL", DEFAULT_QWEN_BASE_URL).rstrip("/")
    model_name = get_setting("QWEN_MODEL", "qwen-plus").strip() or "qwen-plus"
    try:
        timeout_seconds = float(get_setting("AI_TIMEOUT_SECONDS", "30"))
        max_retries = int(get_setting("AI_MAX_RETRIES", "2"))
    except ValueError:
        timeout_seconds = 30.0
        max_retries = 2
    return AISettings(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        timeout_seconds=min(max(timeout_seconds, 5.0), 120.0),
        max_retries=min(max(max_retries, 0), 5),
    )
