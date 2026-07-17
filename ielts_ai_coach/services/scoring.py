"""Deterministic IELTS score validation, calculation, and diagnosis."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


SUBJECTS = ("listening", "reading", "writing", "speaking")
SUBJECT_LABELS = {
    "listening": "听力",
    "reading": "阅读",
    "writing": "写作",
    "speaking": "口语",
}
RECOMMENDATIONS = {
    "listening": [
        "每天进行精听，先独立完成，再对照原文定位漏听和同义替换。",
        "建立数字、日期、拼写和连读错题清单，每周集中复盘。",
    ],
    "reading": [
        "按题型整理错题，记录定位词、同义替换和错误原因。",
        "每周安排限时阅读，训练在规定时间内完成三篇文章。",
    ],
    "writing": [
        "写作前先列出观点和段落功能，确保完整回应题目要求。",
        "完成后按任务回应、衔接、词汇和语法四个维度自查。",
    ],
    "speaking": [
        "每天选择一个话题录制两分钟回答，检查停顿和重复表达。",
        "使用“观点—原因—例子”结构扩展 Part 2 和 Part 3。",
    ],
}


class ScoreValidationError(ValueError):
    """Raised when IELTS section scores are incomplete or invalid."""


@dataclass(frozen=True)
class ScoreDiagnosis:
    """A deterministic diagnosis derived from four IELTS section scores."""

    overall: float
    lowest_score: float
    lowest_subjects: tuple[str, ...]
    overall_gap: float
    subject_gaps: dict[str, float]
    recommendations: dict[str, list[str]]


def is_valid_score(value: float) -> bool:
    """Return whether a score is from 0 to 9 in half-band steps."""

    return 0.0 <= value <= 9.0 and abs(value * 2 - round(value * 2)) < 1e-9


def validate_scores(scores: dict[str, float]) -> None:
    """Validate all four required IELTS section scores."""

    if set(scores) != set(SUBJECTS):
        raise ScoreValidationError("missing_or_extra_subject")
    if any(not is_valid_score(float(scores[subject])) for subject in SUBJECTS):
        raise ScoreValidationError("invalid_score")


def calculate_overall(scores: dict[str, float]) -> float:
    """Calculate IELTS overall using deterministic half-band rounding."""

    validate_scores(scores)
    total = sum(Decimal(str(scores[subject])) for subject in SUBJECTS)
    average = total / Decimal(len(SUBJECTS))
    rounded = (average * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 2
    return float(rounded)


def analyze_scores(
    scores: dict[str, float], target_overall: float
) -> ScoreDiagnosis:
    """Identify all weakest sections and calculate target gaps."""

    validate_scores(scores)
    if not is_valid_score(float(target_overall)):
        raise ScoreValidationError("invalid_target")

    overall = calculate_overall(scores)
    lowest_score = min(float(scores[subject]) for subject in SUBJECTS)
    lowest_subjects = tuple(
        subject
        for subject in SUBJECTS
        if float(scores[subject]) == lowest_score
    )
    return ScoreDiagnosis(
        overall=overall,
        lowest_score=lowest_score,
        lowest_subjects=lowest_subjects,
        overall_gap=max(0.0, round(target_overall - overall, 1)),
        subject_gaps={
            subject: max(0.0, round(target_overall - float(scores[subject]), 1))
            for subject in SUBJECTS
        },
        recommendations={
            subject: RECOMMENDATIONS[subject] for subject in lowest_subjects
        },
    )
