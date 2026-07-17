"""Simplified Chinese seven-day plan with executable task details."""

from __future__ import annotations

from itertools import groupby

import streamlit as st

from ielts_ai_coach.database.models import PlanTask, User
from ielts_ai_coach.services.planning import (
    generate_plan,
    get_active_plan_data,
    get_plan_history,
)
from ielts_ai_coach.services.planning_rules import (
    PHASE_LABELS,
    PlanGenerationError,
)
from ielts_ai_coach.services.task_content import get_task_content
from ielts_ai_coach.views.task_cards import render_plan_task_summary


PLAN_ERRORS = {
    "profile_required": "请先完善学生档案。",
    "score_required": "请先录入至少一次IELTS四科成绩。",
    "exam_in_past": "考试日期已经过去，请先更新学生档案。",
    "invalid_minutes": "每日学习时间无效，请更新学生档案。",
}


def _daily_focus(tasks: list[PlanTask]) -> str:
    """Return the first priority task objective as the day's main focus."""

    if not tasks:
        return "保持学习节奏"
    primary_task = min(tasks, key=lambda task: task.priority)
    return get_task_content(primary_task).objective


def _render_plan_tasks(tasks: tuple[PlanTask, ...]) -> None:
    """Render seven daily sections with concrete task summaries."""

    for task_date, date_tasks_iterator in groupby(
        tasks, key=lambda task: task.task_date
    ):
        date_tasks = list(date_tasks_iterator)
        total_minutes = sum(task.planned_minutes for task in date_tasks)
        with st.expander(
            f"{task_date.isoformat()} · 计划 {total_minutes} 分钟",
            expanded=task_date == tasks[0].task_date,
        ):
            st.info(f"当日训练重点：{_daily_focus(date_tasks)}")
            for index, task in enumerate(date_tasks):
                if index:
                    st.divider()
                render_plan_task_summary(task)


def render_plan_page(user: User) -> None:
    """Render plan generation, the active plan, and version history."""

    plan_data = get_active_plan_data(user.id)
    st.title("七天计划")
    st.caption(
        "计划由确定性规则生成，无需AI API。重新生成会归档旧计划，不删除历史。"
    )

    button_label = "重新生成七天计划" if plan_data else "生成七天计划"
    if st.button(
        button_label,
        type="primary",
        use_container_width=True,
    ):
        try:
            generate_plan(user.id)
        except PlanGenerationError as error:
            st.error(
                PLAN_ERRORS.get(
                    str(error),
                    "计划生成失败，请检查档案和成绩后重试。",
                )
            )
        else:
            st.success("新的七天计划已生成。")
            st.rerun()

    if plan_data is None:
        st.info("完成档案和成绩录入后，即可生成第一份七天计划。")
        return

    phase_label = PHASE_LABELS.get(plan_data.plan.phase, plan_data.plan.phase)
    first, second, third = st.columns(3)
    first.metric("当前阶段", phase_label)
    second.metric("计划周期", "7天")
    third.metric("任务数量", str(len(plan_data.tasks)))
    _render_plan_tasks(plan_data.tasks)

    history = get_plan_history(user.id)
    with st.expander(f"计划历史（{len(history)}份）"):
        for plan in history:
            status = "使用中" if plan.status == "active" else "已归档"
            st.write(
                f"#{plan.id} · {plan.start_date} 至 {plan.end_date} · "
                f"{PHASE_LABELS.get(plan.phase, plan.phase)} · {status}"
            )
