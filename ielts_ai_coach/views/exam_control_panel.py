"""Shared Streamlit controls for timed IELTS practice sessions."""

from __future__ import annotations

import hashlib
import json
from enum import Enum

import streamlit as st
import streamlit.components.v1 as components

from ielts_ai_coach.services.exam_controls import (
    ExamSession,
    ExamStatus,
    pause_exam,
    reconcile_exam,
)


class ExamControlAction(str, Enum):
    """UI actions that a skill page may need to mirror locally."""

    NONE = "none"
    PAUSED = "paused"
    RESUMED = "resumed"
    TIMED_OUT = "timed_out"


def _client_key(session: ExamSession) -> str:
    """Return an opaque browser marker for one controller."""

    return hashlib.sha256(session.session_id.encode("utf-8")).hexdigest()[:16]


def _render_live_timer(
    session: ExamSession,
    *,
    pause_root_key: str | None = None,
) -> None:
    """Keep the visible countdown current without forcing server reruns."""

    client_key = _client_key(session)
    remaining = session.remaining_seconds()
    minutes, seconds = divmod(remaining, 60)
    st.markdown(
        f'<div class="exam-control-status" data-exam-control="{client_key}">'
        f'<strong data-exam-timer>{minutes:02d}:{seconds:02d}</strong>'
        f'<span data-exam-status>{_status_label(session.status)}</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    payload = json.dumps(
        {
            "clientKey": client_key,
            "deadline": session.deadline.isoformat(),
            "status": session.status.value,
            "remaining": remaining,
            "pauseOverlayId": (
                f"exam-hard-pause-{pause_root_key}" if pause_root_key else ""
            ),
            "pauseRootClass": "",
        }
    )
    script = """
    <script>
    (() => {
      const config = __EXAM_CONFIG__;
      const parentWindow = window.parent;
      const attach = () => {
        const root = parentWindow.document.querySelector(
          `[data-exam-control="${config.clientKey}"]`
        );
        if (!root) {
          parentWindow.setTimeout(attach, 100);
          return;
        }
        const display = root.querySelector("[data-exam-timer]");
        const status = root.querySelector("[data-exam-status]");
        const clearPauseLock = () => {
          if (!config.pauseOverlayId) return;
          const stateKey = config.pauseOverlayId + "-state";
          const state = parentWindow[stateKey];
          document.getElementById(config.pauseOverlayId)?.remove();
          document.getElementById(config.pauseOverlayId + "-style")?.remove();
          const pausedRoot = state?.root ||
            document.querySelector("." + config.pauseRootClass) ||
            document.querySelector('[data-testid="stMain"]');
          if (!pausedRoot) return;
          if (state?.hadInertAttribute) pausedRoot.setAttribute("inert", state.inertAttribute);
          else pausedRoot.removeAttribute("inert");
          if ("inert" in pausedRoot) pausedRoot.inert = Boolean(state?.wasInert);
          if (state?.hadAriaHidden) pausedRoot.setAttribute("aria-hidden", state.ariaHidden);
          else pausedRoot.removeAttribute("aria-hidden");
          pausedRoot.style.pointerEvents = state?.pointerEvents || "";
          document.body.style.overflow = state?.bodyOverflow || "";
          document.body.style.touchAction = state?.bodyTouchAction || "";
          state?.panes?.forEach((pane) => {
            pane.element.style.overflow = pane.overflow;
            pane.element.style.overflowY = pane.overflowY;
            pane.element.scrollTop = pane.scrollTop;
            pane.element.scrollLeft = pane.scrollLeft;
          });
          if (state) {
            document.removeEventListener("wheel", state.blockScroll, true);
            document.removeEventListener("touchmove", state.blockScroll, true);
            document.removeEventListener("keydown", state.blockKeyboard, true);
            parentWindow.scrollTo(state.scrollX, state.scrollY);
            delete parentWindow[stateKey];
          }
        };
        clearPauseLock();
        const frozen = ["paused", "timed_out", "submitted"].includes(
          config.status
        );
        const update = () => {
          const seconds = frozen
            ? config.remaining
            : Math.max(0,
                Math.floor((Date.parse(config.deadline) - Date.now()) / 1000)
              );
          display.textContent =
            String(Math.floor(seconds / 60)).padStart(2, "0") + ":" +
            String(seconds % 60).padStart(2, "0");
          if (seconds === 0 && !["submitted"].includes(config.status)) {
            status.textContent = "时间已到";
          }
        };
        update();
        if (!frozen) {
          const timerId = window.setInterval(update, 1000);
          const cleanup = () => {
            window.clearInterval(timerId);
            parentWindow.document.removeEventListener(
              "visibilitychange", update
            );
          };
          window.addEventListener(
            "pagehide",
            cleanup,
            { once: true }
          );
          parentWindow.document.addEventListener("visibilitychange", update);
        }
      };
      attach();
    })();
    </script>
    """.replace("__EXAM_CONFIG__", payload)
    components.html(script, height=0, width=0)


def _status_label(status: ExamStatus) -> str:
    """Translate one controller state for the student UI."""

    return {
        ExamStatus.NOT_STARTED: "未开始",
        ExamStatus.RUNNING: "计时中",
        ExamStatus.PAUSED: "已暂停",
        ExamStatus.SUBMIT_CONFIRM: "等待确认",
        ExamStatus.TIMED_OUT: "时间已到",
        ExamStatus.SUBMITTED: "已提交",
    }[status]


def render_exam_control_panel(
    session: ExamSession,
    *,
    pause_root_key: str | None = None,
) -> tuple[ExamSession, ExamControlAction]:
    """Render a live timer and the transitions shared by all skill pages."""

    reconciled = reconcile_exam(session)
    action = (
        ExamControlAction.TIMED_OUT
        if reconciled.status is ExamStatus.TIMED_OUT
        and session.status is not ExamStatus.TIMED_OUT
        else ExamControlAction.NONE
    )
    session = reconciled
    _render_live_timer(session, pause_root_key=pause_root_key)
    if session.status is ExamStatus.PAUSED:
        return session, action

    if session.status is ExamStatus.RUNNING:
        if st.button(
            "暂停计时",
            key=f"exam_pause_{_client_key(session)}",
            use_container_width=True,
        ):
            session = pause_exam(session)
            action = ExamControlAction.PAUSED
    elif session.status is ExamStatus.TIMED_OUT:
        st.warning("时间已到，答案已锁定。未作答题目将在交卷后计为错误。")
    return session, action
