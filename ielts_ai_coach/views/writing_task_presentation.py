"""Task selection, visual rendering, and session draft helpers for Writing."""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

from ielts_ai_coach.services.writing_tasks import (
    WritingTask,
    get_writing_task,
    list_writing_tasks,
)
from ielts_ai_coach.services.skill_sessions import draft_key


def apply_writing_task_prefill() -> bool:
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


def _remember_visual_choice(
    user_id: int,
    widget_key: str,
    registry_key: str,
) -> None:
    """Save the outgoing draft before changing the active visual task."""

    selected = st.session_state.get(widget_key)
    registry = st.session_state.get("writing_draft_registry")
    if isinstance(selected, str) and isinstance(registry, dict):
        visual_record = registry.setdefault(registry_key, {})
        previous = (
            visual_record.get("visual_task_id")
            if isinstance(visual_record, dict)
            else None
        )
        if isinstance(previous, str) and previous != selected:
            active_key = draft_key(user_id, "writing", previous)
            prompt_key = f"{active_key}_prompt"
            content_key = f"{active_key}_content"
            revision = st.session_state.get(
                f"{content_key}_editor_revision",
                0,
            )
            editor_key = f"{content_key}_editor_{revision}"
            draft_record = registry.setdefault(active_key, {})
            if isinstance(draft_record, dict):
                for field, state_key in (
                    ("prompt", prompt_key),
                    ("content", editor_key),
                ):
                    value = st.session_state.get(state_key)
                    if isinstance(value, str):
                        draft_record[field] = value
        if isinstance(visual_record, dict):
            visual_record["visual_task_id"] = selected
            st.session_state["writing_draft_registry"] = registry


def select_writing_task(
    user_id: int,
    test_type: str,
    task_type: str,
) -> tuple[WritingTask, str]:
    """Select one task and return its isolated session-state key."""

    task_options = list_writing_tasks(test_type, task_type)
    if test_type == "Academic" and task_type == "Task 1":
        task = _select_academic_visual(user_id, task_options)
        state_key = task.task_id
    else:
        task = task_options[0]
        state_key = f"{test_type}-{task_type}"
    st.caption(
        f"{task.title} · 建议 {task.suggested_minutes} 分钟 · "
        f"至少 {task.minimum_words} 词"
    )
    return task, state_key


def _select_academic_visual(
    user_id: int,
    task_options: tuple[WritingTask, ...],
) -> WritingTask:
    """Render the six-option Academic Task 1 visual selector."""

    widget_key = "writing_academic_task1_visual"
    registry_key = f"visual:{user_id}:Academic:Task 1"
    registry = st.session_state.get("writing_draft_registry", {})
    record = registry.get(registry_key, {}) if isinstance(registry, dict) else {}
    task_ids = tuple(task.task_id for task in task_options)
    saved = record.get("visual_task_id") if isinstance(record, dict) else None
    if saved in task_ids and st.session_state.get(widget_key) != saved:
        st.session_state[widget_key] = saved
    selected = st.selectbox(
        "视觉题目",
        task_ids,
        format_func=lambda task_id: next(
            task.title for task in task_options if task.task_id == task_id
        ),
        key=widget_key,
        on_change=_remember_visual_choice,
        args=(user_id, widget_key, registry_key),
    )
    if isinstance(registry, dict):
        current = registry.setdefault(registry_key, {})
        if isinstance(current, dict):
            current["visual_task_id"] = selected
            st.session_state["writing_draft_registry"] = registry
    return get_writing_task("Academic", "Task 1", selected)


def restore_draft_record(
    draft_key: str,
    *,
    prompt_value_key: str,
    content_value_key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Restore stable prompt/content values after page-widget cleanup."""

    registry = st.session_state.get("writing_draft_registry", {})
    record = registry.setdefault(draft_key, {}) if isinstance(registry, dict) else {}
    if isinstance(record, dict):
        for value_key, field in (
            (prompt_value_key, "prompt"),
            (content_value_key, "content"),
        ):
            saved = record.get(field)
            if isinstance(saved, str) and saved and not st.session_state.get(value_key):
                st.session_state[value_key] = saved
    return registry, record


def save_draft_record(
    registry: dict[str, Any],
    record: dict[str, Any],
    *,
    prompt: str,
    content: str,
) -> None:
    """Save one task's current draft in the shared session registry."""

    record["prompt"] = prompt
    record["content"] = content
    st.session_state["writing_draft_registry"] = registry


def prepare_writing_widgets(
    *,
    prompt_key: str,
    prompt_value_key: str,
    content_key: str,
    content_value_key: str,
    revision_key: str,
    control_status_key: str,
    current_control_status: str,
    editable: bool,
    task_changed: bool,
    default_prompt: str,
) -> tuple[str, bool]:
    """Restore widget values around pause/resume and task selection changes."""

    if (
        st.session_state.get(control_status_key) == "paused"
        and current_control_status == "running"
    ):
        st.session_state[revision_key] = int(st.session_state.get(revision_key, 0)) + 1
    editor_key = f"{content_key}_editor_{st.session_state.get(revision_key, 0)}"
    status_changed = st.session_state.get(control_status_key) != current_control_status
    for widget_key, value_key in (
        (prompt_key, prompt_value_key),
        (editor_key, content_value_key),
    ):
        current_value = st.session_state.get(widget_key)
        saved_value = st.session_state.get(value_key)
        has_new_edit = editable and isinstance(current_value, str) and bool(
            current_value.strip()
        )
        if (
            editable
            and (current_value is None or not str(current_value).strip())
            and isinstance(saved_value, str)
            and saved_value.strip()
        ):
            st.session_state[widget_key] = saved_value
        elif status_changed and value_key in st.session_state and not has_new_edit:
            st.session_state[widget_key] = st.session_state[value_key]
        elif (
            editable
            and isinstance(current_value, str)
            and (current_value or not st.session_state.get(value_key))
        ):
            st.session_state[value_key] = current_value
        elif not editable and value_key in st.session_state:
            st.session_state[widget_key] = st.session_state[value_key]
    pending_prompt = st.session_state.pop("writing_pending_prompt", "")
    if pending_prompt:
        st.session_state[prompt_key] = pending_prompt
        st.session_state[prompt_value_key] = pending_prompt
    elif task_changed or prompt_key not in st.session_state:
        st.session_state[prompt_key] = default_prompt
        st.session_state[prompt_value_key] = default_prompt
    return editor_key, status_changed


def render_writing_visual(task: WritingTask) -> None:
    """Render an accessible responsive SVG before the task prompt."""

    if task.visual_asset is None:
        return
    st.markdown("### 视觉材料")
    asset_path = Path(__file__).resolve().parent.parent.parent / task.visual_asset
    image_data = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    with st.container(key="writing_task_visual"):
        st.markdown(
            '<figure class="writing-task-visual">'
            f'<img src="data:image/svg+xml;base64,{image_data}" '
            f'alt="{escape(task.visual_alt or task.title)}">'
            f"<figcaption>{escape(task.visual_alt or '')}</figcaption>"
            "</figure>",
            unsafe_allow_html=True,
        )
