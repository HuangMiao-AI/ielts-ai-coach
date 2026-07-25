"""Simplified Chinese IELTS Level 2 writing-feedback page."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.ai.factory import get_ai_provider
from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.skill_sessions import (
    claim_submission,
    draft_key,
    elapsed_seconds,
    release_submission,
    start_session,
)
from ielts_ai_coach.services.writing import (
    WRITING_DAILY_LIMIT,
    WRITING_DISCLAIMER,
    WritingServiceError,
    count_words,
    get_essay_feedback,
    get_essay_history,
    get_writing_remaining,
    retry_essay,
    save_essay_without_feedback,
    submit_essay,
)
from ielts_ai_coach.services.writing_tasks import (
    get_writing_task,
    inspect_writing_locally,
)
from ielts_ai_coach.views.writing_feedback_view import render_feedback


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
    st.session_state["writing_pending_prompt"] = prompt[:2000]
    return True


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
            "saved": "已保存（未评分）",
        }.get(essay.status, essay.status)
        with st.expander(
            f"#{essay.id} · {essay.task_type} · {essay.word_count}词 · {status_label}"
        ):
            st.caption(essay.prompt)
            st.markdown(essay.content)
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
    st.title("写作练习")
    st.caption("选择原创题目、计时写作并保存历史；AI可用时才进行批改。")
    if was_prefilled:
        st.success("已从今日任务带入原创题目，请完成作文后提交批改。")

    if provider.is_mock:
        st.info(
            "AI评分当前未启用。你仍可完成并保存作文，系统不会生成模拟分数。",
            icon="🧪",
        )
    else:
        st.error(WRITING_DISCLAIMER)
        st.metric("今日剩余批改额度", f"{remaining}/{WRITING_DAILY_LIMIT} 次")

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
    original_task = get_writing_task(test_type, task_type)
    st.caption(
        f"{original_task.title} · 建议 {original_task.suggested_minutes} 分钟 · "
        f"至少 {original_task.minimum_words} 词"
    )
    active_draft_key = draft_key(
        user.id,
        "writing",
        f"{test_type}-{task_type}",
    )
    prompt_key = f"{active_draft_key}_prompt"
    content_key = f"{active_draft_key}_content"
    pending_prompt = st.session_state.pop("writing_pending_prompt", "")
    if pending_prompt:
        st.session_state[prompt_key] = pending_prompt
    elif prompt_key not in st.session_state:
        st.session_state[prompt_key] = original_task.prompt
    prompt = st.text_area(
        "作文题目",
        max_chars=2000,
        height=100,
        placeholder="粘贴完整的IELTS写作题目",
        key=prompt_key,
    )
    content = st.text_area(
        "作文正文",
        max_chars=12000,
        height=320,
        placeholder="在这里输入或粘贴你的英文作文",
        key=content_key,
    )
    word_count = count_words(content)
    st.caption(f"当前字数：{word_count}词")
    threshold = original_task.minimum_words
    if content and word_count < threshold:
        st.warning(f"正文少于{threshold}词，可能影响任务完成度。")
    if content:
        checks = inspect_writing_locally(
            content,
            minimum_words=threshold,
        )
        st.caption(
            f"本地基础检查：{checks.paragraph_count} 段 · "
            f"{'达到' if checks.meets_recommended_length else '未达到'}"
            "建议字数 · 不产生IELTS分数"
        )

    timer_key = f"{active_draft_key}_timer"
    if content and timer_key not in st.session_state:
        st.session_state[timer_key] = start_session(
            user_id=user.id,
            skill="writing",
            task_key=task_type,
            item_count=1,
            duration_seconds=3600,
        )
    timer = st.session_state.get(timer_key)
    if timer is not None:
        seconds = elapsed_seconds(timer)
        st.caption(f"本次编辑用时：{seconds // 60}分{seconds % 60}秒")

    clear_key = f"{active_draft_key}_clear"
    submit_key = f"{active_draft_key}_submit"
    clear_column, submit_column = st.columns(2)
    if clear_column.button("清空草稿", use_container_width=True):
        st.session_state[clear_key] = True
    if submit_column.button(
        "保存作文" if provider.is_mock else "提交AI批改",
        type="primary",
        disabled=(not provider.is_mock and remaining <= 0),
        use_container_width=True,
    ):
        st.session_state[submit_key] = True

    if st.session_state.get(clear_key, False):
        confirmed_clear = st.checkbox(
            "确认清空当前草稿",
            key=f"{clear_key}_confirmed",
        )
        if st.button("执行清空", disabled=not confirmed_clear):
            for key in (prompt_key, content_key, timer_key, clear_key):
                st.session_state.pop(key, None)
            st.rerun()

    if st.session_state.get(submit_key, False):
        st.warning(
            "请确认题目、任务类型和正文无误；保存后可在历史中查看，"
            "不会生成AI评分。"
            if provider.is_mock
            else "请确认题目、任务类型和正文无误；提交后将占用一次成功额度。"
        )
        if st.button(
            "确认保存作文" if provider.is_mock else "确认提交AI批改",
            type="primary",
            use_container_width=True,
        ):
            guard = f"writing-{user.id}-{task_type}"
            if not claim_submission(st.session_state, guard):
                st.info("本次提交正在处理中，请勿重复点击。")
            else:
                try:
                    if provider.is_mock:
                        save_essay_without_feedback(
                            user_id=user.id,
                            test_type=test_type,
                            task_type=task_type,
                            prompt=prompt,
                            content=content,
                        )
                        result = None
                    else:
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
                    st.error(
                        WRITING_ERRORS.get(
                            str(error),
                            "批改失败，作文已安全保留。",
                        )
                    )
                else:
                    st.success(
                        "作文已保存。AI评分当前未启用。"
                        if provider.is_mock
                        else "批改完成。"
                    )
                    st.session_state[submit_key] = False
                    if result is not None:
                        render_feedback(result.feedback)
                finally:
                    release_submission(st.session_state, guard)

    _render_recent_history(user)
