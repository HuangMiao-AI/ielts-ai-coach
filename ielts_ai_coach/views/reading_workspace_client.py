"""Client-only helpers for the live Reading workspace display."""

from __future__ import annotations

import hashlib
import json

import streamlit.components.v1 as components


def reading_workspace_client_key(*, user_id: int, task_id: int) -> str:
    """Return an opaque browser key scoped to one authenticated user/task."""

    value = f"{user_id}:{task_id}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:16]


def render_reading_navigation_client(*, user_id: int, task_id: int) -> None:
    """Attach navigation after the question container is present in the DOM."""

    client_key = reading_workspace_client_key(user_id=user_id, task_id=task_id)
    script = """
    <script>
    (() => {
      const parentWindow = window.parent;
      const parentDocument = parentWindow.document;
      const clientKey = __READING_CLIENT_KEY__;
      let attempts = 0;
      const attach = () => {
      const navigation = parentDocument.querySelector(
        `[data-reading-question-navigation="${clientKey}"]`
      );
      if (!navigation) {
        if (attempts++ < 100) parentWindow.setTimeout(attach, 100);
        return;
      }
      if (navigation.__readingNavigationAttached) return;
      const links = Array.from(
        navigation.querySelectorAll("[data-reading-question-id]")
      );
      const anchors = links.map((link) => parentDocument.querySelector(
        `#reading-question-${link.dataset.readingQuestionId}`
      )).filter(Boolean);
      if (!links.length || !anchors.length) {
        if (attempts++ < 100) parentWindow.setTimeout(attach, 100);
        return;
      }
      navigation.__readingNavigationAttached = true;
      const storageKey = `ielts-reading-active-question-v1:${clientKey}`;
      const setActive = (questionId) => {
        links.forEach((link) => {
          const current = link.dataset.readingQuestionId === questionId;
          link.classList.toggle("current", current);
          link.setAttribute("aria-current", current ? "true" : "false");
        });
        parentWindow.localStorage.setItem(storageKey, questionId);
      };
      const scrollContainer = anchors[0].parentElement?.closest(
        '[data-testid="stVerticalBlock"]'
      );
      links.forEach((link) => link.addEventListener("click", (event) => {
        event.preventDefault();
        const questionId = link.dataset.readingQuestionId;
        const anchor = parentDocument.querySelector(
          `#reading-question-${questionId}`
        );
        setActive(questionId);
        anchor?.scrollIntoView({ behavior: "smooth", block: "start" });
      }));
      const observer = new IntersectionObserver((entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting);
        if (!visible.length) return;
        visible.sort((left, right) => left.boundingClientRect.top - right.boundingClientRect.top);
        setActive(visible[0].target.dataset.readingQuestionId);
      }, { root: scrollContainer, threshold: 0.35 });
      anchors.forEach((anchor) => observer.observe(anchor));
      const stored = parentWindow.localStorage.getItem(storageKey);
      const initial = links.some((link) => link.dataset.readingQuestionId === stored)
        ? stored
        : links.find((link) => link.getAttribute("aria-current") === "true")?.dataset.readingQuestionId;
      if (initial) setActive(initial);
      };
      attach();
    })();
    </script>
    """
    components.html(
        script.replace("__READING_CLIENT_KEY__", json.dumps(client_key)),
        height=0,
    )
