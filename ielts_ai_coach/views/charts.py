"""Reusable Streamlit chart helpers that do not require Pandas."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import ScoreRecord


def render_score_trend(
    history: list[ScoreRecord],
    *,
    title: str = "成绩趋势",
) -> None:
    """Render user-owned IELTS scores as a responsive Vega-Lite chart."""

    if not history:
        st.info("还没有成绩数据，录入模考成绩后即可查看趋势。")
        return
    st.subheader(title)
    chart_rows = [
        {
            "日期": record.recorded_at.date().isoformat(),
            "总分": record.overall,
            "听力": record.listening,
            "阅读": record.reading,
            "写作": record.writing,
            "口语": record.speaking,
        }
        for record in reversed(history)
    ]
    st.vega_lite_chart(
        {
            "data": {"values": chart_rows},
            "transform": [
                {
                    "fold": ["总分", "听力", "阅读", "写作", "口语"],
                    "as": ["科目", "分数"],
                }
            ],
            "mark": {"type": "line", "point": True},
            "encoding": {
                "x": {"field": "日期", "type": "temporal", "title": "记录日期"},
                "y": {
                    "field": "分数",
                    "type": "quantitative",
                    "scale": {"domain": [0, 9]},
                },
                "color": {"field": "科目", "type": "nominal"},
                "tooltip": [
                    {"field": "日期", "type": "temporal"},
                    {"field": "科目", "type": "nominal"},
                    {"field": "分数", "type": "quantitative"},
                ],
            },
        },
        use_container_width=True,
    )
