"""Chinese-first reusable result components for deterministic exam reviews."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import streamlit as st

from ielts_ai_coach.services.review_summary import (
    answer_status,
    build_question_type_analysis,
)


QUESTION_TYPE_LABELS = {
    "multiple_choice": "单项选择",
    "form_completion": "表格填空",
    "note_completion": "笔记填空",
    "true_false_not_given": "判断题",
    "matching_heading": "段落标题匹配",
}


def question_type_label(question_type: str) -> str:
    """Return a student-facing Chinese label for a bank question type."""

    return QUESTION_TYPE_LABELS.get(question_type, "其他题型")


def render_result_overview(
    *,
    subject: str,
    results: Iterable[Any],
    correct_count: int,
    total_questions: int,
    accuracy: float,
    elapsed_seconds: int | None = None,
    writing_status: str | None = None,
) -> None:
    """Render one shared top-level score and completion overview."""

    items = tuple(results)
    answered = sum(bool(str(item.user_answer).strip()) for item in items)
    st.subheader(f"{subject}结果总览")
    metrics = st.columns(6)
    metrics[0].metric("总分", f"{correct_count}/{total_questions}")
    metrics[1].metric(f"{subject}得分", f"{accuracy:.0%}")
    metrics[2].metric("已答题数", f"{answered}/{total_questions}")
    metrics[3].metric("正确率", f"{accuracy:.0%}")
    metrics[4].metric("总耗时", _duration_label(elapsed_seconds))
    metrics[5].metric("状态", writing_status or "已提交")


def render_answer_card(results: Iterable[Any]) -> None:
    """Render all question statuses without exposing answer explanations yet."""

    st.markdown("#### 答案卡")
    columns = st.columns(8)
    for index, result in enumerate(results, start=1):
        status = answer_status(result)
        status_class = {
            "正确": "correct",
            "错误": "incorrect",
            "未作答": "blank",
        }[status]
        columns[(index - 1) % 8].markdown(
            f'<div class="review-answer-chip {status_class}">'
            f"<strong>{index}</strong><span>{status}</span></div>",
            unsafe_allow_html=True,
        )


def render_question_type_analysis(results: Iterable[Any]) -> None:
    """Render correct, total, and accuracy for every existing question type."""

    st.markdown("#### 题型分析")
    for item in build_question_type_analysis(results):
        left, middle, right = st.columns((2, 1, 1))
        left.write(question_type_label(item.question_type))
        middle.write(f"{item.correct}/{item.total} 题正确")
        right.write(f"{item.accuracy:.0%}")


def render_question_explanations(results: Iterable[Any]) -> None:
    """Render Chinese-first, evidence-backed cards for each submitted item."""

    st.markdown("#### 逐题解析")
    for index, result in enumerate(results, start=1):
        status = answer_status(result)
        label = question_type_label(result.question_type)
        with st.expander(f"第 {index} 题 · {label} · {status}"):
            st.write(f"**题目：** {result.question}")
            st.write(f"**你的答案：** {result.user_answer or '未作答'}")
            st.write(f"**正确答案：** {result.correct_answer}")
            st.markdown("**中文解析**")
            st.write(result.explanation_zh)
            st.markdown("**英文原文定位**")
            st.code(result.evidence_text, language=None)
            st.markdown("**定位句中文翻译**")
            st.write(result.evidence_translation_zh)
            st.markdown("**解题逻辑与考点**")
            st.write(result.tested_skill)
            st.markdown("**易错原因**")
            st.write(result.common_mistake_zh)
            st.markdown("**题干与原文对应表达**")
            for prompt, evidence in result.synonym_pairs:
                st.write(f"- {prompt} → {evidence}")


def render_vocabulary(items: Iterable[Any]) -> None:
    """Render bilingual source vocabulary as compact responsive cards."""

    st.markdown("#### 核心词汇")
    for item in items:
        with st.container(border=True):
            st.markdown(f"**{item.word_or_phrase}** · {item.part_of_speech}")
            st.write(f"中文含义：{item.meaning_zh}")
            st.write(f"English meaning: {item.meaning_en}")
            st.caption(f"原文语境：{item.source_context}")
            st.caption(f"同义替换：{item.synonym_or_paraphrase}")
            st.caption(f"雅思考点：{item.ielts_note_zh}")


def render_reading_review(
    score: Any,
    passage: Any,
    *,
    include_overview: bool = True,
) -> None:
    """Render tabs for the existing Reading result, not a second score flow."""

    if include_overview:
        render_result_overview(
            subject="阅读",
            results=score.results,
            correct_count=score.correct_count,
            total_questions=score.total_questions,
            accuracy=score.accuracy,
        )
    answer, analysis, location, intensive, vocabulary = st.tabs(
        ["答案卡", "逐题解析", "原文定位", "文章精读", "核心词汇"]
    )
    with answer:
        render_answer_card(score.results)
        render_question_type_analysis(score.results)
    with analysis:
        render_question_explanations(score.results)
    with location:
        for index, result in enumerate(score.results, start=1):
            st.markdown(f"**第 {index} 题定位句**")
            st.code(result.evidence_text, language=None)
            st.write(result.evidence_translation_zh)
    with intensive:
        for section in passage.sections:
            with st.expander(f"Section {section.label}"):
                st.write(section.text)
    with vocabulary:
        render_vocabulary(passage.vocabulary_items)


def render_listening_review(score: Any, test: Any) -> None:
    """Render tabs for the existing session-only Listening result."""

    render_result_overview(
        subject="听力",
        results=score.results,
        correct_count=score.correct_count,
        total_questions=score.total_questions,
        accuracy=score.accuracy,
    )
    answer, analysis, listening, shadowing, vocabulary = st.tabs(
        ["答案卡", "逐题解析", "原文精听", "原文跟读", "核心词汇"]
    )
    with answer:
        render_answer_card(score.results)
        render_question_type_analysis(score.results)
    with analysis:
        render_question_explanations(score.results)
    with listening:
        _render_scripts(test, show_translation=True)
    with shadowing:
        _render_scripts(test, show_translation=False)
    with vocabulary:
        for section in test.sections:
            st.markdown(f"### {section.title}")
            render_vocabulary(section.vocabulary_items)


def _render_scripts(test: Any, *, show_translation: bool) -> None:
    """Render only verified bundled scripts for active Listening sections."""

    for section in test.sections:
        st.markdown(f"### {section.title}")
        for turn in section.script:
            st.write(f"**{turn.speaker}：** {turn.text}")
            if show_translation:
                st.caption("请结合上方逐题中文解析核对本句中的信息定位。")


def _duration_label(seconds: int | None) -> str:
    """Format optional elapsed duration without inventing missing timing data."""

    if seconds is None:
        return "本次未记录"
    minutes, remainder = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{remainder:02d}"
