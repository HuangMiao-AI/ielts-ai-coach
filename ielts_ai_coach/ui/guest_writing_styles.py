"""Focused CSS for guest entry, session score, and Writing visuals."""

from textwrap import dedent


GUEST_WRITING_CSS = dedent(
    """
    .st-key-guest_cta {
        width: min(100%, 560px); margin: 0 auto 1.2rem; text-align: center;
    }
    .st-key-guest_cta .stButton > button {
        min-height: 66px; font-size: 1.12rem; line-height: 1.35;
        box-shadow: var(--shadow-lift);
    }
    .st-key-auth_form_shell { max-width: 420px; margin-inline: auto; }
    .st-key-guest_status_bar {
        margin-bottom: 1rem; padding: .55rem .75rem;
        border: 1px solid var(--border); border-radius: 14px;
        background: var(--surface);
    }
    .score-chip {
        width: fit-content; min-width: 92px; margin-left: auto;
        padding: .55rem .8rem; border: 1px solid var(--border);
        border-radius: 14px; background: var(--surface); text-align: center;
    }
    .score-chip span { display: block; color: var(--muted); font-size: .76rem; }
    .score-chip strong { color: var(--primary-dark); font-size: 1.35rem; }
    .st-key-writing_task_visual {
        max-width: 100%; padding: .5rem; border: 1px solid var(--border);
        border-radius: 18px; background: var(--surface-strong);
    }
    .st-key-writing_task_visual img, .writing-task-visual {
        display: block; width: 100%; max-width: 100%; height: auto;
        object-fit: contain;
    }
    .writing-task-visual { margin: 0; }
    .writing-task-visual figcaption {
        margin-top: .45rem; color: var(--muted); font-size: .82rem;
        text-align: center;
    }
    @media (max-width: 768px) { .score-chip { margin: 0; } }
    """
).strip()
