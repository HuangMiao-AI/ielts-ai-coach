"""Four-step onboarding and editable learner profile page."""

from __future__ import annotations

from collections.abc import Mapping

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.learner_profiles import get_learner_profile
from ielts_ai_coach.views.learner_profile_form import (
    render_learning_profile_editor,
    render_onboarding,
)


def render_profile_page(
    user: User,
    page_refs: Mapping[str, st.Page],
) -> None:
    """Render onboarding until complete, then the shared profile editor."""

    profile = get_learner_profile(user.id)
    if profile is None or not profile.onboarding_completed:
        render_onboarding(user, page_refs)
        return
    st.title("我的档案")
    st.caption("更新学习目标和可选当前成绩；缺失数据不会自动补齐。")
    render_learning_profile_editor(user, source_key="profile")
