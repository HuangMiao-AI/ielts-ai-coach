"""Simplified Chinese student profile page."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.profiles import (
    GRADE_OPTIONS,
    ProfilePersistenceError,
    ProfileValidationError,
    get_profile,
    save_profile,
)


PROFILE_ERRORS = {
    "invalid_nickname": "昵称长度应为1–40个字符。",
    "invalid_grade": "请选择有效的年级。",
    "invalid_target": "目标分必须是0–9之间的0.5分档。",
    "exam_in_past": "考试日期不能早于今天。",
    "exam_too_far": "考试日期不能超过三年。",
    "invalid_minutes": "每日学习时间应为15–480分钟。",
}
PROFILE_SUCCESS_KEY = "profile_save_success"


def render_profile_page(user: User) -> None:
    """Render and process the current user's profile form."""

    profile = get_profile(user.id)
    st.title("我的档案")
    st.caption("这些信息用于生成诊断、学习计划和个性化建议。")
    if st.session_state.pop(PROFILE_SUCCESS_KEY, False):
        st.success("档案保存成功")

    if profile is None:
        st.info("第一次使用，请先完善学习档案。", icon="👋")

    default_grade = profile.grade if profile else "高二"
    grade_index = (
        GRADE_OPTIONS.index(default_grade)
        if default_grade in GRADE_OPTIONS
        else 0
    )
    today = date.today()
    default_exam_date = profile.exam_date if profile else today + timedelta(days=120)
    maximum_exam_date = today + timedelta(days=366 * 3)

    with st.form("student_profile_form"):
        nickname = st.text_input(
            "姓名或昵称",
            value=profile.nickname if profile else user.username,
            max_chars=40,
        )
        grade = st.selectbox(
            "当前年级或阶段",
            GRADE_OPTIONS,
            index=grade_index,
        )
        target_overall = st.select_slider(
            "IELTS目标总分",
            options=[value / 2 for value in range(0, 19)],
            value=profile.target_overall if profile else 7.0,
        )
        exam_date = st.date_input(
            "计划考试日期",
            value=default_exam_date,
            min_value=today,
            max_value=maximum_exam_date,
        )
        daily_study_minutes = st.slider(
            "每天可学习时间",
            min_value=15,
            max_value=480,
            value=profile.daily_study_minutes if profile else 90,
            step=15,
            format="%d 分钟",
        )
        submitted = st.form_submit_button(
            "保存档案",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    try:
        save_profile(
            user_id=user.id,
            nickname=nickname,
            grade=grade,
            target_overall=float(target_overall),
            exam_date=exam_date,
            daily_study_minutes=daily_study_minutes,
        )
    except ProfileValidationError as error:
        st.error(PROFILE_ERRORS.get(str(error), "档案信息无效，请检查后重试。"))
    except ProfilePersistenceError:
        st.error("档案保存失败：数据库暂时不可用，请稍后重试。")
    else:
        st.session_state[PROFILE_SUCCESS_KEY] = True
        st.rerun()
