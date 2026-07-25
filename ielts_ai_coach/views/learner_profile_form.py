"""Shared four-step onboarding and learner-settings editor."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.learner_profiles import (
    LearnerProfileSnapshot,
    LearnerProfileValidationError,
    get_learner_profile,
    save_learner_profile,
)
from ielts_ai_coach.services.profiles import GRADE_OPTIONS


BAND_VALUES = tuple(value / 2 for value in range(19))
BAND_OPTIONS: tuple[str | float, ...] = ("未填写", *BAND_VALUES)
STEP_LABELS = ("基本信息", "当前成绩（可选）", "学习目标", "确认保存")
ERROR_MESSAGES = {
    "invalid_display_name": "姓名或昵称长度应为1–40个字符。",
    "invalid_grade": "请选择有效的年级。",
    "invalid_band": "成绩必须是0–9之间的0.5分档。",
    "invalid_minutes": "每日学习时间应为15–480分钟。",
    "exam_in_past": "考试日期不能早于今天。",
    "exam_too_far": "考试日期不能超过三年。",
}


def _step_key(user_id: int) -> str:
    """Return the user-scoped onboarding step key."""

    return f"onboarding_{user_id}_step"


def _draft_key(user_id: int) -> str:
    """Return the user-scoped onboarding draft key."""

    return f"onboarding_{user_id}_draft"


def _draft(user: User) -> dict[str, Any]:
    """Return a bounded mutable draft for the active user."""

    key = _draft_key(user.id)
    value = st.session_state.get(key)
    if not isinstance(value, dict):
        value = {
            "display_name": user.username,
            "current_grade": "高二",
            "current_listening_band": None,
            "current_reading_band": None,
            "current_writing_band": None,
            "current_speaking_band": None,
            "target_overall_band": 7.0,
            "exam_date": None,
            "daily_study_minutes": 90,
        }
        st.session_state[key] = value
    return value


def _render_step_header(step: int) -> None:
    """Render one compact four-step progress indicator."""

    st.progress(step / 4, text=f"步骤 {step}/4 · {STEP_LABELS[step - 1]}")
    st.caption(f"步骤 {step}/4 · {STEP_LABELS[step - 1]}")


def _band_option(value: float | None) -> str | float:
    """Map a nullable band to the select control's explicit empty option."""

    return "未填写" if value is None else float(value)


def _band_value(value: str | float) -> float | None:
    """Map one select value to the persistent nullable band contract."""

    return None if value == "未填写" else float(value)


def _grade_index(value: str) -> int:
    """Return a safe grade index."""

    return GRADE_OPTIONS.index(value) if value in GRADE_OPTIONS else 0


def _band_index(value: float | None) -> int:
    """Return the index of a nullable band in the shared options."""

    return BAND_OPTIONS.index(_band_option(value))


def _render_basic_step(user: User, draft: dict[str, Any]) -> None:
    """Collect the student's display identity."""

    display_name = st.text_input(
        "姓名或昵称",
        value=str(draft["display_name"]),
        max_chars=40,
        key=f"onboarding_{user.id}_display_name",
    )
    grade = st.selectbox(
        "当前年级或阶段",
        GRADE_OPTIONS,
        index=_grade_index(str(draft["current_grade"])),
        key=f"onboarding_{user.id}_grade",
    )
    if st.button("下一步", type="primary", use_container_width=True):
        if not display_name.strip():
            st.error(ERROR_MESSAGES["invalid_display_name"])
            return
        draft["display_name"] = display_name.strip()
        draft["current_grade"] = grade
        st.session_state[_step_key(user.id)] = 2
        st.rerun()


def _render_score_step(user: User, draft: dict[str, Any]) -> None:
    """Collect independently optional current skill baselines."""

    st.info("没有近期成绩可以全部留空；系统不会用默认分数补齐。")
    fields = (
        ("listening", "当前听力成绩"),
        ("reading", "当前阅读成绩"),
        ("writing", "当前写作成绩"),
        ("speaking", "当前口语成绩"),
    )
    columns = st.columns(2)
    values: dict[str, float | None] = {}
    for index, (skill, label) in enumerate(fields):
        with columns[index % 2]:
            selected = st.selectbox(
                label,
                BAND_OPTIONS,
                index=_band_index(draft[f"current_{skill}_band"]),
                key=f"onboarding_{user.id}_{skill}_band",
            )
            values[skill] = _band_value(selected)
    back, next_column = st.columns(2)
    if back.button("上一步", use_container_width=True):
        st.session_state[_step_key(user.id)] = 1
        st.rerun()
    if next_column.button("下一步", type="primary", use_container_width=True):
        for skill, value in values.items():
            draft[f"current_{skill}_band"] = value
        st.session_state[_step_key(user.id)] = 3
        st.rerun()


def _render_goal_step(user: User, draft: dict[str, Any]) -> None:
    """Collect target, optional date, and available study time."""

    target = st.selectbox(
        "目标总分",
        BAND_VALUES,
        index=BAND_VALUES.index(float(draft["target_overall_band"])),
        key=f"onboarding_{user.id}_target",
    )
    no_exam_date = st.checkbox(
        "暂未确定考试日期",
        value=draft["exam_date"] is None,
        key=f"onboarding_{user.id}_no_exam_date",
    )
    exam_date: date | None = None
    if not no_exam_date:
        default_date = draft["exam_date"]
        if not isinstance(default_date, date):
            default_date = date.today() + timedelta(days=120)
        exam_date = st.date_input(
            "计划考试日期",
            value=default_date,
            min_value=date.today(),
            max_value=date.today() + timedelta(days=366 * 3),
            key=f"onboarding_{user.id}_exam_date",
        )
    minutes = st.slider(
        "每天可学习时间",
        min_value=15,
        max_value=480,
        value=int(draft["daily_study_minutes"]),
        step=15,
        format="%d 分钟",
        key=f"onboarding_{user.id}_minutes",
    )
    back, next_column = st.columns(2)
    if back.button("上一步", use_container_width=True):
        st.session_state[_step_key(user.id)] = 2
        st.rerun()
    if next_column.button("下一步", type="primary", use_container_width=True):
        draft["target_overall_band"] = float(target)
        draft["exam_date"] = exam_date
        draft["daily_study_minutes"] = int(minutes)
        st.session_state[_step_key(user.id)] = 4
        st.rerun()


def _render_review_step(
    user: User,
    draft: dict[str, Any],
    page_refs: Mapping[str, st.Page],
) -> None:
    """Review and persist the complete onboarding draft."""

    st.markdown(f"**姓名：** {draft['display_name']}")
    st.markdown(f"**阶段：** {draft['current_grade']}")
    st.markdown(f"**目标总分：** {draft['target_overall_band']:.1f}")
    exam_label = (
        draft["exam_date"].isoformat()
        if isinstance(draft["exam_date"], date)
        else "暂未确定"
    )
    st.markdown(f"**考试日期：** {exam_label}")
    labels = {
        "listening": "听力",
        "reading": "阅读",
        "writing": "写作",
        "speaking": "口语",
    }
    score_text = " · ".join(
        f"{label} "
        f"{draft[f'current_{skill}_band']:.1f}"
        if draft[f"current_{skill}_band"] is not None
        else f"{label} 未填写"
        for skill, label in labels.items()
    )
    st.markdown(f"**当前成绩：** {score_text}")
    back, save_column = st.columns(2)
    if back.button("上一步", use_container_width=True):
        st.session_state[_step_key(user.id)] = 3
        st.rerun()
    if not save_column.button(
        "保存并进入首页",
        type="primary",
        use_container_width=True,
    ):
        return
    try:
        save_learner_profile(
            user_id=user.id,
            display_name=str(draft["display_name"]),
            current_grade=str(draft["current_grade"]),
            exam_date=draft["exam_date"],
            daily_study_minutes=int(draft["daily_study_minutes"]),
            target_overall_band=float(draft["target_overall_band"]),
            current_reading_band=draft["current_reading_band"],
            current_listening_band=draft["current_listening_band"],
            current_writing_band=draft["current_writing_band"],
            current_speaking_band=draft["current_speaking_band"],
            onboarding_completed=True,
        )
    except LearnerProfileValidationError as error:
        st.error(ERROR_MESSAGES.get(str(error), "资料无效，请检查后重试。"))
        return
    st.session_state[f"onboarding_{user.id}_saved"] = True
    st.session_state.pop(_step_key(user.id), None)
    st.session_state.pop(_draft_key(user.id), None)
    st.switch_page(page_refs["home"])


def render_onboarding(
    user: User,
    page_refs: Mapping[str, st.Page],
) -> None:
    """Render the correct step for a new user's persistent setup."""

    st.title("开始设置学习档案")
    st.caption("四步完成基本设置，成绩和考试日期均可暂时留空。")
    step = st.session_state.get(_step_key(user.id), 1)
    if not isinstance(step, int) or step not in {1, 2, 3, 4}:
        step = 1
    st.session_state[_step_key(user.id)] = step
    draft = _draft(user)
    _render_step_header(step)
    if step == 1:
        _render_basic_step(user, draft)
    elif step == 2:
        _render_score_step(user, draft)
    elif step == 3:
        _render_goal_step(user, draft)
    else:
        _render_review_step(user, draft, page_refs)


def render_learning_profile_editor(
    user: User,
    *,
    source_key: str,
) -> None:
    """Render one shared editable V2/legacy learning-settings form."""

    profile = get_learner_profile(user.id)
    if profile is None:
        st.info("请先完成学习档案设置。")
        return
    no_date_default = profile.exam_date is None
    with st.form(f"learner_profile_editor_{source_key}_{user.id}"):
        display_name = st.text_input(
            "姓名或昵称",
            value=profile.display_name,
            max_chars=40,
        )
        grade = st.selectbox(
            "当前年级或阶段",
            GRADE_OPTIONS,
            index=_grade_index(profile.current_grade),
        )
        columns = st.columns(2)
        selected_bands: dict[str, str | float] = {}
        for index, (skill, label) in enumerate(
            (
                ("listening", "当前听力成绩"),
                ("reading", "当前阅读成绩"),
                ("writing", "当前写作成绩"),
                ("speaking", "当前口语成绩"),
            )
        ):
            with columns[index % 2]:
                selected_bands[skill] = st.selectbox(
                    label,
                    BAND_OPTIONS,
                    index=_band_index(profile.current_band(skill)),
                )
        target = st.selectbox(
            "目标总分",
            BAND_VALUES,
            index=BAND_VALUES.index(profile.target_overall_band),
        )
        no_exam_date = st.checkbox(
            "暂未确定考试日期",
            value=no_date_default,
        )
        exam_date: date | None = None
        if not no_exam_date:
            exam_date = st.date_input(
                "计划考试日期",
                value=profile.exam_date
                or date.today() + timedelta(days=120),
                min_value=date.today(),
                max_value=date.today() + timedelta(days=366 * 3),
            )
        minutes = st.slider(
            "每天可学习时间",
            min_value=15,
            max_value=480,
            value=profile.daily_study_minutes,
            step=15,
            format="%d 分钟",
        )
        label = "保存档案" if source_key == "profile" else "保存学习设置"
        submitted = st.form_submit_button(
            label,
            type="primary",
            use_container_width=True,
        )
    if not submitted:
        return
    try:
        save_learner_profile(
            user_id=user.id,
            display_name=display_name,
            current_grade=grade,
            exam_date=exam_date,
            daily_study_minutes=minutes,
            target_overall_band=float(target),
            current_reading_band=_band_value(selected_bands["reading"]),
            current_listening_band=_band_value(selected_bands["listening"]),
            current_writing_band=_band_value(selected_bands["writing"]),
            current_speaking_band=_band_value(selected_bands["speaking"]),
            onboarding_completed=True,
        )
    except LearnerProfileValidationError as error:
        st.error(ERROR_MESSAGES.get(str(error), "资料无效，请检查后重试。"))
    else:
        st.success("学习设置已保存。")

