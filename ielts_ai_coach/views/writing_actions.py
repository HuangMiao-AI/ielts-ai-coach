"""Writing draft clearing, submission, and recent-history actions."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from ielts_ai_coach.ai.base import AIProvider
from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.exam_controls import (
    ExamSession,
    ExamStatus,
    cancel_submission as cancel_control_submission,
    clear_exam_control,
    mark_submitted as mark_control_submitted,
    request_submission as request_control_submission,
    save_exam_control,
)
from ielts_ai_coach.services.skill_sessions import (
    claim_submission,
    release_submission,
)
from ielts_ai_coach.services.writing import (
    WritingServiceError,
    get_essay_feedback,
    get_essay_history,
    retry_essay,
    save_essay_without_feedback,
    submit_essay,
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


@dataclass(frozen=True)
class WritingDraftKeys:
    """All transient keys owned by one writing task draft."""

    prompt: str
    content: str
    prompt_value: str
    content_value: str
    clear: str
    submit: str
    control_status: str


def render_recent_history(user: User) -> None:
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
            f"#{essay.id} · {essay.task_type} · "
            f"{essay.word_count}词 · {status_label}"
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
                                str(error),
                                "批改失败，请稍后重试。",
                            )
                        )
                    else:
                        st.rerun()


def _save_control(
    user: User,
    task_key: str,
    control: ExamSession,
) -> None:
    """Persist one Writing controller in the active session."""

    save_exam_control(
        st.session_state,
        user_id=user.id,
        task_key=task_key,
        session=control,
    )


def render_writing_actions(
    *,
    user: User,
    provider: AIProvider,
    remaining: int,
    test_type: str,
    task_type: str,
    prompt: str,
    content: str,
    control: ExamSession | None,
    control_task_key: str,
    keys: WritingDraftKeys,
) -> None:
    """Render clear and submit actions for one controlled writing draft."""

    clear_column, submit_column = st.columns(2)
    if clear_column.button("清空草稿", use_container_width=True):
        st.session_state[keys.clear] = True
    if submit_column.button(
        "保存作文" if provider.is_mock else "提交AI批改",
        type="primary",
        disabled=(
            (not provider.is_mock and remaining <= 0)
            or control is None
            or control.status
            not in {ExamStatus.RUNNING, ExamStatus.TIMED_OUT}
        ),
        use_container_width=True,
    ):
        assert control is not None
        control = request_control_submission(control)
        _save_control(user, control_task_key, control)
        st.session_state[keys.submit] = True

    if st.session_state.get(keys.clear, False):
        confirmed_clear = st.checkbox(
            "确认清空当前草稿",
            key=f"{keys.clear}_confirmed",
        )
        if st.button("执行清空", disabled=not confirmed_clear):
            for key in vars(keys).values():
                st.session_state.pop(key, None)
            clear_exam_control(
                st.session_state,
                user_id=user.id,
                skill="writing",
                task_key=control_task_key,
            )
            st.rerun()

    if not st.session_state.get(keys.submit, False):
        return
    if control is not None and control.status is ExamStatus.TIMED_OUT:
        control = request_control_submission(control)
        _save_control(user, control_task_key, control)
    st.warning(
        "请确认题目、任务类型和正文无误；保存后可在历史中查看，"
        "不会生成AI评分。"
        if provider.is_mock
        else "请确认题目、任务类型和正文无误；提交后将占用一次成功额度。"
    )
    back, confirm = st.columns(2)
    if back.button("返回编辑", use_container_width=True):
        if control is not None:
            _save_control(
                user,
                control_task_key,
                cancel_control_submission(control),
            )
        st.session_state[keys.submit] = False
        st.rerun()
    if not confirm.button(
        "确认保存作文" if provider.is_mock else "确认提交AI批改",
        type="primary",
        use_container_width=True,
    ):
        return
    guard = f"writing-{user.id}-{task_type}"
    if not claim_submission(st.session_state, guard):
        st.info("本次提交正在处理中，请勿重复点击。")
        return
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
        st.session_state[keys.submit] = False
        if control is not None:
            _save_control(
                user,
                control_task_key,
                mark_control_submitted(control),
            )
        if result is not None:
            render_feedback(result.feedback)
    finally:
        release_submission(st.session_state, guard)
