"""Simplified Chinese IELTS Level 2 writing-feedback page."""
from __future__ import annotations

import streamlit as st

from ielts_ai_coach.ai.factory import get_ai_provider
from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.exam_controls import (
    ExamSession,
    ExamStatus,
    exam_control_key,
    load_exam_control,
    resume_exam,
    save_exam_control,
)
from ielts_ai_coach.services.skill_sessions import draft_key
from ielts_ai_coach.services.writing import (
    WRITING_DAILY_LIMIT,
    WRITING_DISCLAIMER,
    count_words,
    get_writing_remaining,
)
from ielts_ai_coach.services.writing_tasks import inspect_writing_locally
from ielts_ai_coach.views.exam_control_panel import (
    ExamControlAction,
    render_exam_control_panel,
)
from ielts_ai_coach.views.exam_hard_pause import (
    render_hard_pause_overlay,
)
from ielts_ai_coach.views.writing_actions import (
    WritingDraftKeys,
    render_recent_history,
    render_writing_actions,
)
from ielts_ai_coach.views.writing_feedback_view import render_feedback
from ielts_ai_coach.views.guest_writing_actions import render_guest_writing_actions
from ielts_ai_coach.views.writing_task_presentation import (
    apply_writing_task_prefill,
    render_writing_visual,
    prepare_writing_widgets,
    restore_draft_record,
    save_draft_record,
    select_writing_task,
)


def render_writing_page(user: User, *, guest_mode: bool = False) -> None:
    """Render essay submission, structured feedback, and recent history."""
    provider = get_ai_provider()
    remaining = 0 if guest_mode else get_writing_remaining(user.id)
    was_prefilled = apply_writing_task_prefill()
    st.title("写作练习")
    st.caption("选择原创题目、计时写作并保存历史；AI可用时才进行批改。")
    if was_prefilled:
        st.success("已从今日任务带入原创题目，请完成作文后提交批改。")

    if guest_mode:
        st.info("游客模式下，草稿和本次结果只保存在当前会话。")
    elif provider.is_mock:
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
    original_task, task_state_key = select_writing_task(
        user.id,
        test_type,
        task_type,
    )
    active_draft_key = draft_key(
        user.id,
        "writing",
        task_state_key,
    )
    prompt_key = f"{active_draft_key}_prompt"
    content_key = f"{active_draft_key}_content"
    prompt_value_key = f"{prompt_key}_value"
    content_value_key = f"{content_key}_value"
    draft_registry, draft_record = restore_draft_record(
        active_draft_key,
        prompt_value_key=prompt_value_key,
        content_value_key=content_value_key,
    )
    revision_key = f"{content_key}_editor_revision"
    content_editor_key = f"{content_key}_editor_{st.session_state.get(revision_key, 0)}"
    control_task_key = task_state_key
    control_key = exam_control_key(
        user.id,
        "writing",
        control_task_key,
    )
    control_status_key = f"{control_key}_last_status"
    selected_task_key = f"{active_draft_key}_selected_task"
    task_changed = st.session_state.get(selected_task_key) != original_task.task_id
    st.session_state[selected_task_key] = original_task.task_id
    control: ExamSession | None = None
    existing_content = (
        st.session_state.get(content_editor_key)
        or st.session_state.get(content_key)
        or st.session_state.get(content_value_key)
    )
    if (
        isinstance(existing_content, str)
        and existing_content.strip()
    ) or control_key in st.session_state:
        control = load_exam_control(
            st.session_state,
            user_id=user.id,
            skill="writing",
            task_key=control_task_key,
            duration_seconds=original_task.suggested_minutes * 60,
        )
        root_key = f"exam_root_writing_{user.id}_{control_task_key}"
        control, action = render_exam_control_panel(
            control,
            pause_root_key=root_key,
        )
        save_exam_control(
            st.session_state,
            user_id=user.id,
            task_key=control_task_key,
            session=control,
        )
        if control.status is ExamStatus.PAUSED:
            for widget_key, value_key in (
                (prompt_key, prompt_value_key),
                (content_key, content_value_key),
            ):
                current_value = st.session_state.get(widget_key)
                saved_value = st.session_state.get(value_key)
                if isinstance(current_value, str) and (
                    current_value.strip()
                    or not isinstance(saved_value, str)
                    or not saved_value.strip()
                ):
                    st.session_state[value_key] = current_value
            if render_hard_pause_overlay(
                control,
                subject="写作",
                root_key=root_key,
            ):
                control = resume_exam(control)
                save_exam_control(
                    st.session_state,
                    user_id=user.id,
                    task_key=control_task_key,
                    session=control,
                )
                st.rerun()
            st.session_state[control_status_key] = control.status.value
            return
        if action in {
            ExamControlAction.PAUSED,
            ExamControlAction.RESUMED,
        }:
            st.rerun()
    editable = (
        control is None
        or control.status is ExamStatus.RUNNING
    )
    current_control_status = (
        control.status.value if control is not None else "not_started"
    )
    content_editor_key, status_changed = prepare_writing_widgets(
        prompt_key=prompt_key,
        prompt_value_key=prompt_value_key,
        content_key=content_key,
        content_value_key=content_value_key,
        revision_key=revision_key,
        control_status_key=control_status_key,
        current_control_status=current_control_status,
        editable=editable,
        task_changed=task_changed,
        default_prompt=original_task.prompt,
    )
    render_writing_visual(original_task)
    st.markdown("### 题目说明")
    prompt = st.text_area(
        "作文题目",
        max_chars=2000,
        height=100,
        placeholder="粘贴完整的IELTS写作题目",
        key=prompt_key,
        disabled=not editable,
    )
    st.markdown("### 写作输入区")
    content = st.text_area(
        "作文正文",
        max_chars=12000,
        height=320,
        placeholder="在这里输入或粘贴你的英文作文",
        key=content_editor_key,
        disabled=not editable,
    )
    if editable and not status_changed:
        st.session_state[prompt_value_key] = prompt
        if content or not st.session_state.get(content_value_key):
            st.session_state[content_value_key] = content
    else:
        prompt = str(st.session_state.get(prompt_value_key, prompt))
        content = str(st.session_state.get(content_value_key, content))
    save_draft_record(
        draft_registry,
        draft_record,
        prompt=prompt,
        content=content,
    )
    st.session_state[control_status_key] = current_control_status
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

    if content and control is None:
        control = load_exam_control(
            st.session_state,
            user_id=user.id,
            skill="writing",
            task_key=control_task_key,
            duration_seconds=original_task.suggested_minutes * 60,
        )

    keys = WritingDraftKeys(
        prompt=prompt_key,
        content=content_editor_key,
        prompt_value=prompt_value_key,
        content_value=content_value_key,
        clear=f"{active_draft_key}_clear",
        submit=f"{active_draft_key}_submit",
        control_status=control_status_key,
        registry=active_draft_key,
    )
    if guest_mode:
        render_guest_writing_actions(
            guest=user,  # type: ignore[arg-type]
            content=content,
            minimum_words=threshold,
            control=control,
            control_task_key=control_task_key,
            keys=keys,
        )
    else:
        render_writing_actions(
            user=user,
            provider=provider,
            remaining=remaining,
            test_type=test_type,
            task_type=task_type,
            prompt=prompt,
            content=content,
            control=control,
            control_task_key=control_task_key,
            keys=keys,
        )
        render_recent_history(user)
