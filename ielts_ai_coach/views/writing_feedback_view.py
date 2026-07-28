"""Chinese-first presentation of one existing structured Writing feedback record."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.ai.writing_evaluator import WRITING_DISCLAIMER
from ielts_ai_coach.database.models import WritingFeedback


_DIMENSIONS = (
    ("任务回应", "task_response_or_achievement", "是否完整回应题目、展开观点并给出相关支持。"),
    ("连贯衔接", "coherence_and_cohesion", "段落推进、指代和连接是否清楚自然。"),
    ("词汇资源", "lexical_resource", "用词是否准确、多样，并符合正式写作语境。"),
    ("语法准确", "grammatical_range_and_accuracy", "句式变化、时态和基础错误控制情况。"),
)
_EXPRESSIONS = (
    ("A clear trend emerges when …", "用于概括图表或论证中的主要趋势。"),
    ("This can be attributed to …", "用于解释原因，后面接名词或动名词。"),
    ("While …, it is important to note that …", "用于让步和补充限制条件。"),
    ("The evidence suggests that …", "用于基于材料得出谨慎结论。"),
)
_VOCABULARY = (
    ("demonstrate", "动词：表明、证明", "比 show 更正式，适合描述数据或论据。"),
    ("allocate", "动词：分配", "常用于政府、时间或资源分配。"),
    ("significant", "形容词：显著的", "描述变化幅度时注意不要和 slightly 混用。"),
    ("whereas", "连词：然而、而", "连接两个对比鲜明的完整分句。"),
    ("therefore", "副词：因此", "表示逻辑结果，前后要有明确因果关系。"),
    ("illustrate", "动词：说明、阐明", "用于引出例子或解释抽象观点。"),
    ("consistent", "形容词：一致的、持续的", "可描述趋势、政策或论证立场。"),
    ("contrast", "名词/动词：对比", "搭配 in contrast 或 contrast A with B。"),
)


def render_feedback(feedback: WritingFeedback) -> None:
    """Render existing scoring once, then organize its review in Chinese-first tabs."""

    if feedback.provider.casefold() == "mock":
        st.warning("示例反馈：固定本地样例，不代表真实 AI 评分或官方成绩。")
    st.error(WRITING_DISCLAIMER)
    report, chinese, revise, expressions, vocabulary = st.tabs(
        ["评分报告", "中文反馈", "逐项修改", "高分表达", "核心词汇"]
    )
    with report:
        _render_score_report(feedback)
    with chinese:
        _render_chinese_feedback(feedback)
    with revise:
        _render_revision_plan(feedback)
    with expressions:
        _render_expressions()
    with vocabulary:
        _render_vocabulary()


def _render_score_report(feedback: WritingFeedback) -> None:
    """Show the stored model dimensions without calculating another score."""

    st.subheader("写作评分报告")
    columns = st.columns(5)
    for column, (label, field, _) in zip(columns[:4], _DIMENSIONS):
        column.metric(label, f"{getattr(feedback, field):.1f}")
    columns[4].metric("预估总分", f"{feedback.estimated_overall:.1f}")
    st.caption("以上为已保存的单次结构化反馈展示，不会在本页面重新评分。")


def _render_chinese_feedback(feedback: WritingFeedback) -> None:
    """Explain each stored dimension before exposing the original feedback wording."""

    st.subheader("中文反馈总览")
    for label, field, description in _DIMENSIONS:
        score = float(getattr(feedback, field))
        status = "当前相对强项" if score >= feedback.estimated_overall else "优先提升项"
        st.markdown(f"**{label} · {score:.1f} · {status}**")
        st.write(description)
    left, right = st.columns(2)
    with left:
        st.markdown("#### 做得好的地方")
        for item in feedback.strengths:
            st.write(f"- {item}")
    with right:
        st.markdown("#### 主要问题")
        for item in feedback.main_issues:
            st.write(f"- {item}")


def _render_revision_plan(feedback: WritingFeedback) -> None:
    """Turn the saved suggestions into a concrete, ordered revision checklist."""

    st.subheader("逐项修改")
    for index, item in enumerate(feedback.actionable_suggestions, start=1):
        with st.container(border=True):
            st.markdown(f"**第 {index} 步：{item}**")
            st.caption("修改后请检查：这处改动是否让观点、衔接、用词或语法更清楚。")
    st.markdown("#### 单段改写示例")
    st.info(feedback.rewrite_example)


def _render_expressions() -> None:
    """Offer fixed bilingual usage notes without claiming they were in the essay."""

    st.subheader("高分表达")
    st.caption("以下为可迁移表达，不是对本次作文新增评分。")
    for expression, note in _EXPRESSIONS:
        with st.container(border=True):
            st.markdown(f"**{expression}**")
            st.write(note)


def _render_vocabulary() -> None:
    """Present a compact bilingual writing vocabulary set."""

    st.subheader("核心词汇")
    for word, meaning, note in _VOCABULARY:
        with st.container(border=True):
            st.markdown(f"**{word}** · {meaning}")
            st.caption(note)
