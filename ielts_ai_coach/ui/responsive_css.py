"""Extra responsive CSS fragments kept separate from shared visual tokens."""

from __future__ import annotations


DESKTOP_AND_COMPACT_CSS = """
        .reading-workspace-status {
            position: sticky; top: .5rem; z-index: 4; margin: .35rem 0 .75rem;
            padding: .6rem .8rem; border: 1px solid var(--border);
            border-radius: 14px; color: var(--primary-dark);
            background: var(--surface-strong); box-shadow: var(--shadow-soft);
            backdrop-filter: blur(var(--glass-blur));
        }
        .reading-workspace { min-width: 0; }
        [class*="st-key-reading_workspace_"] [data-testid="stHorizontalBlock"] {
            align-items: flex-start;
        }
        [class*="st-key-reading_workspace_"] [data-testid="stVerticalBlockBorderWrapper"] {
            min-width: 0; overflow-y: auto; overscroll-behavior: contain;
            scrollbar-gutter: stable;
        }
        .reading-question-navigation {
            display: flex; flex-wrap: wrap; gap: .38rem; margin: .3rem 0 .65rem;
        }
        .reading-question-link {
            display: inline-grid; width: 2.15rem; min-height: 2.15rem;
            place-items: center; border: 1px solid var(--border); border-radius: 10px;
            color: var(--muted); background: var(--surface-strong); font-weight: 800;
            text-decoration: none;
        }
        .reading-question-link.answered { color: #0B5F59; background: rgba(159, 226, 216, .34); }
        .reading-question-link.current { outline: 2px solid var(--accent); outline-offset: 1px; }
        .reading-question-anchor { scroll-margin-top: 8rem; }
        .reading-pane-divider {
            position: absolute; z-index: 8; top: 3.25rem; bottom: .5rem;
            width: .9rem; margin-left: -.45rem; padding: 0; border: 0;
            cursor: col-resize; background: transparent;
        }
        .reading-pane-divider::after {
            display: block; width: 3px; height: 100%; margin: 0 auto;
            border-radius: 99px; background: rgba(15, 118, 110, .35); content: "";
        }

        @media (min-width: 1366px) {
            .block-container { padding-top: 2.25rem; padding-bottom: 4rem; }
            .section-heading { margin-top: 2rem; }
        }

        @media (max-width: 375px) {
            .block-container { padding-inline: .75rem; }
            .st-key-mobile_bottom_navigation { right: .4rem; left: .4rem; }
            .st-key-mobile_bottom_navigation [data-testid="stPageLink"] a {
                font-size: .7rem;
            }
        }

        @media (max-width: 768px) {
            [class*="st-key-reading_workspace_"] [data-testid="stHorizontalBlock"] {
                flex-direction: column;
            }
            [class*="st-key-reading_workspace_"] [data-testid="stColumn"] {
                width: 100% !important; min-width: 0 !important; flex: 1 1 100% !important;
            }
            .reading-question-link { width: 2rem; min-height: 2rem; }
            .reading-pane-divider { display: none; }
        }
""".strip()
