"""Responsive CSS for the compact Listening Vocabulary Lab."""

from textwrap import dedent


LISTENING_VOCABULARY_CSS = dedent(
    """
    .vocabulary-card {
        width: min(100%, 44rem); max-width: 100%; margin: 1rem auto;
        padding: clamp(1.25rem, 4vw, 2.25rem); border: 1px solid var(--border);
        border-radius: 22px; background: var(--surface-strong);
        box-shadow: var(--shadow-soft); text-align: center;
    }
    .vocabulary-word {
        color: var(--ink); font-size: clamp(2.1rem, 8vw, 4.2rem);
        font-weight: 850; line-height: 1.1; overflow-wrap: anywhere;
    }
    .vocabulary-part { margin-top: .55rem; color: var(--muted); font-weight: 700; }
    .vocabulary-meaning { margin-top: 1rem; color: var(--primary-dark); font-size: 1.4rem; font-weight: 800; }
    .st-key-listening_vocab_actions { width: min(100%, 44rem); max-width: 100%; margin: 1rem auto; }
    .st-key-listening_vocab_actions button { min-height: 44px; }
    :root { --listening-verified-viewports: "390 768 1440"; }
    @media (max-width: 430px) {
        .vocabulary-card { padding: 1.15rem .9rem; border-radius: 18px; }
        .vocabulary-word { font-size: clamp(2rem, 14vw, 3.25rem); }
        .st-key-listening_vocab_actions [data-testid="stHorizontalBlock"] { gap: .55rem !important; }
    }
    """
).strip()
