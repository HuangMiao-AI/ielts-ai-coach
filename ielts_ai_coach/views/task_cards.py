"""Reusable Streamlit renderers for concrete study-task content."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import PlanTask
from ielts_ai_coach.services.question_bank import ReadingPassage, ReadingQuestion
from ielts_ai_coach.services.reading_scoring import ReadingScore
from ielts_ai_coach.services.scoring import SUBJECT_LABELS
from ielts_ai_coach.services.task_content import TaskContent, get_task_content


def _render_original_practice(
    content: TaskContent,
    *,
    reveal_answers: bool,
) -> None:
    """Render original reading or speaking material and delayed answers."""

    if not content.practice_content and not content.questions:
        return
    with st.expander("查看练习内容", expanded=True):
        if content.practice_content:
            st.markdown("**原创短文**")
            st.write(content.practice_content)
        if content.questions:
            st.markdown("**题目**")
            for question in content.questions:
                st.write(question)
    if content.answer_key:
        if reveal_answers:
            with st.expander("查看答案与解析"):
                for index, answer in enumerate(content.answer_key):
                    st.markdown(f"**{answer}**")
                    if index < len(content.explanations):
                        st.caption(content.explanations[index])
        else:
            st.caption("🔒 标记任务完成后可查看答案与解析。")


def render_full_task_card(
    task: PlanTask,
    *,
    reveal_answers: bool,
    show_embedded_practice: bool = True,
) -> TaskContent:
    """Render all information needed to execute one task."""

    content = get_task_content(task)
    st.subheader(content.task_title)
    st.markdown(
        f'<span class="task-time-badge">计划 {task.planned_minutes} 分钟</span>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"{SUBJECT_LABELS.get(task.subject, task.subject)} · "
        f"{content.difficulty} · 优先级 {task.priority}"
    )
    st.markdown("**训练目标**")
    st.write(content.objective)
    st.markdown("**使用材料**")
    st.write(content.material)
    if show_embedded_practice:
        _render_original_practice(content, reveal_answers=reveal_answers)
    with st.expander("查看训练步骤", expanded=True):
        for index, instruction in enumerate(content.instructions, start=1):
            st.write(f"{index}. {instruction}")
    st.markdown("**需要保存的结果**")
    st.write(content.expected_output)
    st.markdown("**完成标准**")
    st.success(content.completion_criteria)
    return content


def render_reading_passage(passage: ReadingPassage) -> None:
    """Render original passage text without any answer material."""

    st.subheader(passage.title)
    st.caption(
        f"{passage.passage_id} · 版本 {passage.version} · "
        f"约 {passage.word_count} 词"
    )
    st.info(
        "本练习由 IELTS AI Coach 项目原创，不是官方 IELTS 或 "
        "Cambridge 真题。"
    )
    with st.container(border=True):
        for section in passage.sections:
            st.markdown(f"**{section.label}**")
            st.write(section.text)


def collect_reading_answers(
    passage: ReadingPassage,
    *,
    task_id: int,
    draft_answers: dict[str, str] | None = None,
) -> dict[str, str]:
    """Render answer controls and return only answers selected by the user."""

    type_labels = {
        "multiple_choice": "Multiple Choice",
        "true_false_not_given": "True / False / Not Given",
        "matching_heading": "Matching Heading",
    }
    answers: dict[str, str] = {}
    st.subheader("问题")
    current_type = ""
    draft = draft_answers or {}
    for index, question in enumerate(passage.questions, start=1):
        if question.question_type != current_type:
            current_type = question.question_type
            st.markdown(f"#### {type_labels[current_type]}")
        st.markdown(f"**{index}. {question.question}**")
        widget_key = f"reading_answer_{task_id}_{question.question_id}"
        if widget_key not in st.session_state and question.question_id in draft:
            st.session_state[widget_key] = draft[question.question_id]
        answer = st.radio(
            f"第 {index} 题答案",
            options=question.options,
            index=None,
            key=widget_key,
        )
        if answer is not None:
            answers[question.question_id] = answer
    return answers


def render_reading_result(score: ReadingScore) -> None:
    """Render the score and complete review only after submission."""

    st.subheader("练习结果")
    score_column, correct_column, accuracy_column = st.columns(3)
    score_column.metric("总分", f"{score.correct_count}/{score.total_questions}")
    correct_column.metric("正确数量", score.correct_count)
    accuracy_column.metric("正确率", f"{score.accuracy:.0%}")

    for index, result in enumerate(score.results, start=1):
        icon = "✅" if result.is_correct else "❌"
        with st.expander(
            f"{icon} 第 {index} 题 · "
            f"{'回答正确' if result.is_correct else '回答错误'}",
            expanded=not result.is_correct,
        ):
            st.write(result.question)
            st.write(f"**你的答案：** {result.user_answer or '未作答'}")
            st.write(f"**正确答案：** {result.correct_answer}")
            st.write(f"**解析：** {result.explanation}")
            st.write(f"**原文证据：** {result.evidence}")


def render_reading_exam_question(
    question: ReadingQuestion,
    *,
    index: int,
    total: int,
    widget_key: str,
    saved_answer: str = "",
    disabled: bool = False,
) -> str:
    """Render one exam question without exposing answer material."""

    if saved_answer and widget_key not in st.session_state:
        st.session_state[widget_key] = saved_answer
    st.caption(f"第 {index} 题，共 {total} 题")
    st.markdown(f"### {question.question}")
    answer = st.radio(
        f"第 {index} 题答案",
        options=question.options,
        index=None,
        key=widget_key,
        disabled=disabled,
    )
    return answer or ""


def render_reading_result_summary(score: ReadingScore) -> None:
    """Render score metrics and deterministic weakness by question type."""

    score_column, correct_column, accuracy_column = st.columns(3)
    score_column.metric("总分", f"{score.correct_count}/{score.total_questions}")
    correct_column.metric("正确数量", score.correct_count)
    accuracy_column.metric("正确率", f"{score.accuracy:.0%}")

    labels = {
        "multiple_choice": "单项选择",
        "true_false_not_given": "判断题",
        "matching_heading": "段落标题匹配",
    }
    totals: dict[str, int] = {}
    errors: dict[str, int] = {}
    for result in score.results:
        totals[result.question_type] = totals.get(result.question_type, 0) + 1
        if not result.is_correct:
            errors[result.question_type] = errors.get(result.question_type, 0) + 1
    if not errors:
        st.success("本次所有题型均作答正确。")
        return
    weakest = max(errors, key=lambda key: errors[key] / totals[key])
    st.warning(
        f"需要优先复盘：{labels.get(weakest, weakest)}"
        f"（错 {errors[weakest]}/{totals[weakest]} 题）。"
    )


def render_plan_task_summary(task: PlanTask) -> None:
    """Render a compact but actionable task inside the seven-day plan."""

    content = get_task_content(task)
    status = "✅" if task.status == "completed" else "⬜"
    st.markdown(f"{status} **{content.task_title}**")
    st.markdown(
        f'<span class="task-time-badge">计划 {task.planned_minutes} 分钟</span>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"{SUBJECT_LABELS.get(task.subject, task.subject)} · "
        f"{content.difficulty}"
    )
    st.write(f"**训练目标：** {content.objective}")
    st.write(f"**完成标准：** {content.completion_criteria}")
    with st.expander("材料与步骤"):
        st.write(f"**材料：** {content.material}")
        for index, instruction in enumerate(content.instructions, start=1):
            st.write(f"{index}. {instruction}")
