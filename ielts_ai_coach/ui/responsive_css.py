"""Extra responsive CSS fragments kept separate from shared visual tokens."""

from __future__ import annotations


DESKTOP_AND_COMPACT_CSS = """
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
""".strip()
