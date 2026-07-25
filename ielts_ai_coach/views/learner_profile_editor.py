"""Editable V2 and legacy-compatible learner settings form."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.learner_profiles import (
    LearnerProfileValidationError,
    get_learner_profile,
    save_learner_profile,
)
from ielts_ai_coach.services.profiles import GRADE_OPTIONS
from ielts_ai_coach.views.learner_profile_fields import (
    BAND_OPTIONS,
    BAND_VALUES,
    ERROR_MESSAGES,
    band_index,
    band_value,
    grade_index,
)


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
    with st.form(f"learner_profile_editor_{source_key}_{user.id}"):
        display_name = st.text_input(
            "姓名或昵称", value=profile.display_name, max_chars=40
        )
        grade = st.selectbox(
            "当前年级或阶段",
            GRADE_OPTIONS,
            index=grade_index(profile.current_grade),
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
                    index=band_index(profile.current_band(skill)),
                )
        target = st.selectbox(
            "目标总分",
            BAND_VALUES,
            index=BAND_VALUES.index(profile.target_overall_band),
        )
        no_exam_date = st.checkbox(
            "暂未确定考试日期", value=profile.exam_date is None
        )
        exam_date: date | None = None
        if not no_exam_date:
            exam_date = st.date_input(
                "计划考试日期",
                value=profile.exam_date or date.today() + timedelta(days=120),
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
            label, type="primary", use_container_width=True
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
            current_reading_band=band_value(selected_bands["reading"]),
            current_listening_band=band_value(selected_bands["listening"]),
            current_writing_band=band_value(selected_bands["writing"]),
            current_speaking_band=band_value(selected_bands["speaking"]),
            onboarding_completed=True,
        )
    except LearnerProfileValidationError as error:
        st.error(ERROR_MESSAGES.get(str(error), "资料无效，请检查后重试。"))
    else:
        st.success("学习设置已保存。")
