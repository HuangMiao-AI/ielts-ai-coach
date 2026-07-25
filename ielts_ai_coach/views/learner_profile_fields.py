"""Shared controls and validation copy for learner profile views."""

from __future__ import annotations

from ielts_ai_coach.services.profiles import GRADE_OPTIONS


BAND_VALUES = tuple(value / 2 for value in range(19))
BAND_OPTIONS: tuple[str | float, ...] = ("未填写", *BAND_VALUES)
ERROR_MESSAGES = {
    "invalid_display_name": "姓名或昵称长度应为1–40个字符。",
    "invalid_grade": "请选择有效的年级。",
    "invalid_band": "成绩必须是0–9之间的0.5分档。",
    "invalid_minutes": "每日学习时间应为15–480分钟。",
    "exam_in_past": "考试日期不能早于今天。",
    "exam_too_far": "考试日期不能超过三年。",
}


def band_option(value: float | None) -> str | float:
    """Map a nullable band to the select control's explicit empty option."""

    return "未填写" if value is None else float(value)


def band_value(value: str | float) -> float | None:
    """Map one select value to the persistent nullable band contract."""

    return None if value == "未填写" else float(value)


def grade_index(value: str) -> int:
    """Return a safe grade index for the configured choices."""

    return GRADE_OPTIONS.index(value) if value in GRADE_OPTIONS else 0


def band_index(value: float | None) -> int:
    """Return the nullable band's index in the shared options."""

    return BAND_OPTIONS.index(band_option(value))
