"""Client-only resize handle for the desktop Reading split workspace."""

from __future__ import annotations

import json

import streamlit.components.v1 as components


_STORAGE_KEY = "ielts-reading-workspace-ratio-v1"


def render_workspace_resizer(*, user_id: int, task_id: int) -> None:
    """Attach one client-only 35–65% resize handle to the active workspace."""

    selector = (
        f'[class*="st-key-reading_workspace_{user_id}_{task_id}"]'
    )
    script = """
    <script>
    (() => {
      const parentWindow = window.parent;
      const parentDocument = parentWindow.document;
      const workspaceSelector = __WORKSPACE_SELECTOR__;
      const storageKey = __STORAGE_KEY__;
      let attempts = 0;

      const attach = () => {
        const workspace = parentDocument.querySelector(workspaceSelector);
        const row = workspace?.querySelector('[data-testid="stHorizontalBlock"]');
        const columns = row ? Array.from(row.children).filter(
          (child) => child.getAttribute('data-testid') === 'stColumn'
        ) : [];
        if (!row || columns.length !== 2) {
          if (attempts++ < 20) parentWindow.setTimeout(attach, 100);
          return;
        }
        if (row.querySelector('.reading-pane-divider')) return;

        row.style.position = 'relative';
        row.style.flexWrap = 'nowrap';
        const divider = parentDocument.createElement('button');
        divider.type = 'button';
        divider.className = 'reading-pane-divider';
        divider.setAttribute('aria-label', '拖动调整文章与题目宽度');
        divider.setAttribute('title', '拖动调整文章与题目宽度');
        row.appendChild(divider);

        const stored = Number(parentWindow.localStorage.getItem(storageKey));
        let ratio = Number.isFinite(stored) && stored >= 0.35 && stored <= 0.65
          ? stored : 0.55;
        const applyRatio = () => {
          columns[0].style.flex = `0 0 calc(${ratio * 100}% - .38rem)`;
          columns[1].style.flex = `0 0 calc(${(1 - ratio) * 100}% - .38rem)`;
          divider.style.left = `calc(${ratio * 100}% - .38rem)`;
        };
        const resize = (event) => {
          const bounds = row.getBoundingClientRect();
          ratio = Math.min(0.65, Math.max(0.35, (event.clientX - bounds.left) / bounds.width));
          applyRatio();
        };
        const stop = () => {
          parentWindow.localStorage.setItem(storageKey, String(ratio));
          parentWindow.removeEventListener('pointermove', resize);
          parentWindow.removeEventListener('pointerup', stop);
        };
        divider.addEventListener('pointerdown', (event) => {
          event.preventDefault();
          parentWindow.addEventListener('pointermove', resize);
          parentWindow.addEventListener('pointerup', stop, { once: true });
        });
        applyRatio();
      };
      attach();
    })();
    </script>
    """
    components.html(
        script.replace("__WORKSPACE_SELECTOR__", json.dumps(selector)).replace(
            "__STORAGE_KEY__", json.dumps(_STORAGE_KEY)
        ),
        height=0,
    )
