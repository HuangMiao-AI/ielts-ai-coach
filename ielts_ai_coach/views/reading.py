"""Reading practice entry page."""

from __future__ import annotations

from collections.abc import Mapping

import streamlit as st

from ielts_ai_coach.database.models import User


def render_reading_page(
    user: User,
    page_refs: Mapping[str, st.Page],
) -> None:
    """Render the reading library entry while preserving today's flow."""

    del user
    st.title("阅读练习")
    st.caption("原创 IELTS 风格练习，非官方 IELTS 或 Cambridge 试题。")
    st.info("阅读考试工作台正在本分支中升级，现有练习流程仍可正常使用。")
    st.page_link(
        page_refs["today"],
        label="打开今日阅读任务",
        icon=":material/arrow_forward:",
        use_container_width=True,
    )
