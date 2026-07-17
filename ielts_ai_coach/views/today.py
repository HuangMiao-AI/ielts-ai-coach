"""Simplified Chinese page for today's concrete study tasks."""

from __future__ import annotations

from datetime import date
from typing import Mapping

import streamlit as st

from ielts_ai_coach.database.models import PlanTask, User
from ielts_ai_coach.services.task_content import TaskContent
from ielts_ai_coach.services.reading_practice import (
    ReadingPracticeError,
    ReadingPracticeState,
    get_reading_practice_state,
    submit_reading_practice,
)
from ielts_ai_coach.services.tasks import (
    TaskUpdateError,
    cancel_task_completion,
    complete_task,
    get_tasks_for_day,
)
from ielts_ai_coach.views.task_cards import (
    collect_reading_answers,
    render_full_task_card,
    render_reading_passage,
    render_reading_result,
)


def _show_task_flash() -> None:
    """Show the result of an action that triggered a Streamlit rerun."""

    message = st.session_state.pop("task_action_success", "")
    if message:
        st.success(message)


def _open_writing_task(
    content: TaskContent,
    page_refs: Mapping[str, object] | None,
) -> None:
    """Save trusted prompt fields and open the writing feedback page."""

    st.session_state["writing_task_prefill"] = {
        "test_type": content.writing_test_type,
        "task_type": content.writing_task_type,
        "prompt": content.writing_prompt,
    }
    writing_page = page_refs.get("writing") if page_refs else None
    if writing_page is not None:
        st.switch_page(writing_page)
    else:
        st.info("题目已准备好，请打开“写作批改”页面继续。")


def _render_writing_link(
    content: TaskContent,
    page_refs: Mapping[str, object] | None,
    task_id: int,
) -> None:
    """Render a full-width writing-page action for writing tasks."""

    if not content.writing_prompt:
        return
    if st.button(
        "带题目去写作批改",
        key=f"open_writing_task_{task_id}",
        use_container_width=True,
    ):
        _open_writing_task(content, page_refs)


def _render_pending_task(user: User, task: PlanTask) -> None:
    """Render one-click completion with an optional time override."""

    edit_actual = st.checkbox(
        "修改实际用时（可选）",
        key=f"edit_actual_minutes_{task.id}",
    )
    actual_minutes: int | None = None
    if edit_actual:
        actual_minutes = int(
            st.number_input(
                "实际学习分钟",
                min_value=1,
                max_value=720,
                value=task.planned_minutes,
                step=5,
                key=f"actual_minutes_{task.id}",
            )
        )
    else:
        st.caption(
            f"一键完成将按计划用时 {task.planned_minutes} 分钟记录，"
            "无需手动填写。"
        )

    if st.button(
        "标记完成",
        type="primary",
        use_container_width=True,
        key=f"complete_task_{task.id}",
    ):
        try:
            complete_task(
                user_id=user.id,
                task_id=task.id,
                actual_minutes=actual_minutes,
            )
        except TaskUpdateError as error:
            message = (
                "实际用时必须在1—720分钟之间。"
                if str(error) == "invalid_minutes"
                else "任务更新失败，请刷新页面后重试。"
            )
            st.error(message)
        else:
            st.session_state["task_action_success"] = "任务已完成，学习时间已记录。"
            st.rerun()


def _render_completed_task(user: User, task: PlanTask) -> None:
    """Render completion status and synchronized cancellation."""

    st.success(f"已完成 · 实际学习 {task.actual_minutes or 0} 分钟")
    if st.button(
        "取消完成",
        key=f"cancel_task_{task.id}",
        use_container_width=True,
    ):
        try:
            cancel_task_completion(user_id=user.id, task_id=task.id)
        except TaskUpdateError:
            st.error("任务更新失败，请刷新页面后重试。")
        else:
            st.session_state["task_action_success"] = (
                "已取消完成，对应学习记录已同步撤销。"
            )
            st.rerun()


def _has_reading_draft(state: ReadingPracticeState) -> bool:
    """Return whether any answer widget currently holds a draft selection."""

    draft = st.session_state.get(f"reading_draft_{state.task.id}", {})
    return isinstance(draft, dict) and bool(draft)


def _render_reading_practice(
    user: User,
    state: ReadingPracticeState,
) -> None:
    """Render the start, continue, submit, and persisted-result states."""

    if state.score is not None:
        st.success(
            "练习已提交，任务完成状态和学习时间已同步保存。"
        )
        render_reading_result(state.score)
        return

    open_key = f"reading_practice_open_{state.task.id}"
    if not st.session_state.get(open_key, False):
        button_label = "继续练习" if _has_reading_draft(state) else "开始练习"
        if st.button(
            button_label,
            type="primary",
            use_container_width=True,
            key=f"open_reading_practice_{state.task.id}",
        ):
            st.session_state[open_key] = True
            st.rerun()
        return

    render_reading_passage(state.passage)
    draft_key = f"reading_draft_{state.task.id}"
    saved_draft = st.session_state.get(draft_key, {})
    answers = collect_reading_answers(
        state.passage,
        task_id=state.task.id,
        draft_answers=saved_draft if isinstance(saved_draft, dict) else None,
    )
    st.session_state[draft_key] = answers
    answered_count = len(answers)
    total_questions = len(state.passage.questions)
    st.caption(f"作答进度：{answered_count}/{total_questions}")

    return_column, submit_column = st.columns(2)
    with return_column:
        if st.button(
            "暂存并返回任务",
            use_container_width=True,
            key=f"pause_reading_practice_{state.task.id}",
        ):
            st.session_state[open_key] = False
            st.rerun()
    with submit_column:
        submitted = st.button(
            "提交答案",
            type="primary",
            use_container_width=True,
            disabled=answered_count != total_questions,
            key=f"submit_reading_practice_{state.task.id}",
        )

    if answered_count != total_questions:
        st.info("请完成所有问题后再提交。提交前不会显示答案和解析。")
    if not submitted:
        return
    try:
        submit_reading_practice(
            user_id=user.id,
            task_id=state.task.id,
            answers=answers,
        )
    except ReadingPracticeError as error:
        if str(error) == "already_submitted":
            st.session_state["task_action_success"] = (
                "本练习已经提交，正在加载已保存结果。"
            )
            st.rerun()
        st.error("答案提交失败，请刷新页面后重试。")
    else:
        st.session_state[open_key] = False
        st.session_state.pop(draft_key, None)
        st.session_state["task_action_success"] = (
            "答案已提交并完成自动评分，学习记录已同步保存。"
        )
        st.rerun()


def render_today_page(
    user: User,
    page_refs: Mapping[str, object] | None = None,
) -> None:
    """Render all active-plan tasks for today."""

    today = date.today()
    tasks = get_tasks_for_day(user.id, task_date=today)
    st.title("今日任务")
    st.caption(f"{today.isoformat()} · 按步骤完成后可一键记录学习时间。")
    _show_task_flash()

    if not tasks:
        st.info("今天还没有任务。请先进入“七天计划”生成学习计划。")
        return

    completed = sum(task.status == "completed" for task in tasks)
    st.progress(completed / len(tasks), text=f"今日进度：{completed}/{len(tasks)}")

    for task in tasks:
        with st.container(border=True):
            reading_state = get_reading_practice_state(
                user_id=user.id,
                task_id=task.id,
            )
            content = render_full_task_card(
                task,
                reveal_answers=(
                    task.status == "completed" and reading_state is None
                ),
                show_embedded_practice=reading_state is None,
            )
            _render_writing_link(content, page_refs, task.id)
            if reading_state is not None:
                _render_reading_practice(user, reading_state)
            elif task.status == "completed":
                _render_completed_task(user, task)
            else:
                _render_pending_task(user, task)
