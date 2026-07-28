"""Behavior contracts for Chinese-first deterministic review summaries."""

from __future__ import annotations

from types import SimpleNamespace

from ielts_ai_coach.services.review_summary import (
    answer_status,
    build_question_type_analysis,
)
from ielts_ai_coach.views.review_components import QUESTION_TYPE_LABELS


def test_question_type_analysis_counts_answers_correctness_and_blanks() -> None:
    """The shared result summary groups each existing question type correctly."""

    results = (
        SimpleNamespace(
            question_type="multiple_choice",
            is_correct=True,
            user_answer="A",
        ),
        SimpleNamespace(
            question_type="multiple_choice",
            is_correct=False,
            user_answer="B",
        ),
        SimpleNamespace(
            question_type="form_completion",
            is_correct=False,
            user_answer="",
        ),
    )

    analysis = build_question_type_analysis(results)

    assert [(item.question_type, item.correct, item.total) for item in analysis] == [
        ("multiple_choice", 1, 2),
        ("form_completion", 0, 1),
    ]
    assert analysis[0].accuracy == 0.5
    assert answer_status(results[0]) == "正确"
    assert answer_status(results[1]) == "错误"
    assert answer_status(results[2]) == "未作答"


def test_review_components_keep_chinese_labels_for_current_question_types() -> None:
    """Existing Reading and Listening types must never fall back to raw keys."""

    assert QUESTION_TYPE_LABELS["multiple_choice"] == "单项选择"
    assert QUESTION_TYPE_LABELS["true_false_not_given"] == "判断题"
    assert QUESTION_TYPE_LABELS["matching_heading"] == "段落标题匹配"
    assert QUESTION_TYPE_LABELS["form_completion"] == "表格填空"
    assert QUESTION_TYPE_LABELS["note_completion"] == "笔记填空"
