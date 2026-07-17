"""Simplified Chinese IELTS Level 2 writing-feedback page."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.ai.factory import get_ai_provider
from ielts_ai_coach.database.models import User, WritingFeedback
from ielts_ai_coach.services.writing import (
    WRITING_DAILY_LIMIT,
    WRITING_DISCLAIMER,
    WritingServiceError,
    count_words,
    get_essay_feedback,
    get_essay_history,
    get_writing_remaining,
    retry_essay,
    submit_essay,
)


WRITING_ERRORS = {
    "invalid_test_type": "请选择有效的考试类型。",
    "invalid_task_type": "请选择Task 1或Task 2。",
    "invalid_prompt": "请输入题目，最多2000个字符。",
    "invalid_content": "请输入作文正文，最多12000个字符。",
    "quota_exhausted": "今天的写作批改额度已用完，请明天再来。",
    "essay_not_found": "找不到这篇作文，或你没有访问权限。",
    "essay_not_retryable": "只有处理失败的作文可以重新批改。",
    "invalid_ai_json": "AI反馈结构无效，作文已保留，可以稍后重试。",
    "network_unavailable": "AI服务暂时无法连接，作文已保留，可以稍后重试。",
}


def _apply_writing_task_prefill() -> bool:
    """Load a trusted writing-plan prompt into stable form widget keys."""

    prefill = st.session_state.pop("writing_task_prefill", None)
    if not isinstance(prefill, dict):
        return False
    test_type = prefill.get("test_type")
    task_type = prefill.get("task_type")
    prompt = prefill.get("prompt")
    if (
        test_type not in {"Academic", "General"}
        or task_type not in {"Task 1", "Task 2"}
        or not isinstance(prompt, str)
        or not prompt.strip()
    ):
        return False
    st.session_state["writing_test_type"] = test_type
    st.session_state["writing_task_type"] = task_type
    st.session_state["writing_prompt"] = prompt[:2000]
    return True


def render_feedback(feedback: WritingFeedback) -> None:
    """Render one validated structured writing report."""

    st.error(WRITING_DISCLAIMER)
    columns = st.columns(5)
    labels = (
        ("任务回应", feedback.task_response_or_achievement),
        ("连贯衔接", feedback.coherence_and_cohesion),
        ("词汇资源", feedback.lexical_resource),
        ("语法准确", feedback.grammatical_range_and_accuracy),
        ("预估总分", feedback.estimated_overall),
    )
    for column, (label, score) in zip(columns, labels):
        column.metric(label, f"{score:.1f}")

    first, second = st.columns(2)
    with first:
        st.subheader("做得好的地方")
        for item in feedback.strengths:
            st.write(f"- {item}")
    with second:
        st.subheader("主要问题")
        for item in feedback.main_issues:
            st.write(f"- {item}")
    st.subheader("具体修改建议")
    for item in feedback.actionable_suggestions:
        st.write(f"- {item}")
    st.subheader("单段改写示例")
    st.info(feedback.rewrite_example)


def _render_recent_history(user: User) -> None:
    """Render recent user-owned essays and retry controls."""

    essays = get_essay_history(user.id)
    if not essays:
        return
    st.divider()
    st.subheader("最近提交")
    for essay in essays[:5]:
        status_label = {
            "pending": "处理中",
            "completed": "已完成",
            "failed": "处理失败",
        }.get(essay.status, essay.status)
        with st.expander(
            f"#{essay.id} · {essay.task_type} · {essay.word_count}词 · {status_label}"
        ):
            st.caption(essay.prompt)
            feedback_records = get_essay_feedback(
                user_id=user.id,
                essay_id=essay.id,
            )
            if feedback_records:
                render_feedback(feedback_records[0])
            elif essay.status == "failed":
                if st.button("重新批改", key=f"retry_essay_{essay.id}"):
                    try:
                        retry_essay(user_id=user.id, essay_id=essay.id)
                    except WritingServiceError as error:
                        st.error(
                            WRITING_ERRORS.get(
                                str(error), "批改失败，请稍后重试。"
                            )
                        )
                    else:
                        st.rerun()


def render_writing_page(user: User) -> None:
    """Render essay submission, structured feedback, and recent history."""

    provider = get_ai_provider()
    remaining = get_writing_remaining(user.id)
    was_prefilled = _apply_writing_task_prefill()
    st.title("写作批改")
    st.caption("按IELTS四项标准提供Level 2学习反馈，并保存历史记录。")
    st.error(WRITING_DISCLAIMER)
    if was_prefilled:
        st.success("已从今日任务带入原创题目，请完成作文后提交批改。")

    if provider.is_mock:
        st.info(
            "当前为演示模式：未配置Qwen API Key，反馈为固定示例，不代表真实水平。",
            icon="🧪",
        )
    st.metric("今日剩余批改额度", f"{remaining}/{WRITING_DAILY_LIMIT} 次")

    with st.form("writing_submission_form"):
        first, second = st.columns(2)
        test_type = first.selectbox(
            "考试类型",
            ("Academic", "General"),
            key="writing_test_type",
        )
        task_type = second.selectbox(
            "写作任务",
            ("Task 1", "Task 2"),
            key="writing_task_type",
        )
        prompt = st.text_area(
            "作文题目",
            max_chars=2000,
            height=100,
            placeholder="粘贴完整的IELTS写作题目",
            key="writing_prompt",
        )
        content = st.text_area(
            "作文正文",
            max_chars=12000,
            height=320,
            placeholder="在这里粘贴你的英文作文",
            key="writing_content",
        )
        word_count = count_words(content)
        st.caption(f"当前字数：{word_count}词")
        threshold = 150 if task_type == "Task 1" else 250
        if content and word_count < threshold:
            st.warning(f"正文少于{threshold}词，可能影响任务完成度。")
        submitted = st.form_submit_button(
            "提交AI批改",
            type="primary",
            use_container_width=True,
            disabled=remaining <= 0,
        )

    if submitted:
        try:
            with st.spinner("正在分析作文，请稍候..."):
                result = submit_essay(
                    user_id=user.id,
                    test_type=test_type,
                    task_type=task_type,
                    prompt=prompt,
                    content=content,
                    provider=provider,
                )
        except WritingServiceError as error:
            st.error(WRITING_ERRORS.get(str(error), "批改失败，作文已安全保留。"))
        else:
            st.success("批改完成。")
            render_feedback(result.feedback)

    _render_recent_history(user)
