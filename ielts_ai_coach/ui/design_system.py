"""Shared visual tokens and CSS for the student application."""

from __future__ import annotations

from textwrap import dedent


DESIGN_TOKENS: dict[str, str | int] = {
    "color_ink": "#102A2E",
    "color_text": "#102A2E",
    "color_muted": "#587176",
    "color_primary": "#0F766E",
    "color_primary_dark": "#0B5F59",
    "color_accent": "#E6A15A",
    "color_border": "rgba(88, 113, 118, 0.20)",
    "color_surface": "rgba(255, 255, 255, 0.82)",
    "surface_strong": "rgba(255, 255, 255, 0.94)",
    "touch_target_px": 44,
    "content_max_px": 1240,
    "radius_card": 20,
}


def build_app_css() -> str:
    """Return the complete responsive application stylesheet."""

    tokens = DESIGN_TOKENS
    return dedent(
        f"""
        <style>
        :root {{
            --ink: {tokens["color_ink"]}; --text: {tokens["color_text"]};
            --muted: {tokens["color_muted"]}; --primary: {tokens["color_primary"]};
            --primary-dark: {tokens["color_primary_dark"]};
            --accent: {tokens["color_accent"]}; --border: {tokens["color_border"]};
            --surface: {tokens["color_surface"]}; --surface-strong: {tokens["surface_strong"]};
            --glass-blur: 18px; --touch-target: {tokens["touch_target_px"]}px;
            --content-max: {tokens["content_max_px"]}px; --card-radius: {tokens["radius_card"]}px;
            --shadow-soft: 0 18px 50px rgba(16, 42, 46, 0.09);
            --shadow-lift: 0 22px 60px rgba(15, 118, 110, 0.14);
            --supported-viewports: "375 430 768 1024 1366 1440 1920";
        }}

        html, body, .stApp, [data-testid="stAppViewContainer"] {{
            max-width: 100%;
            color: var(--text);
            overflow-x: hidden;
        }}

        .stApp {{
            background:
                radial-gradient(circle at 92% 2%, rgba(159, 226, 216, .42), transparent 30rem),
                radial-gradient(circle at 8% 94%, rgba(247, 210, 164, .24), transparent 28rem),
                linear-gradient(155deg, #f3faf8 0%, #f7fbfc 52%, #fffaf4 100%);
        }}

        .block-container {{
            width: min(100%, var(--content-max));
            padding: 2rem clamp(1rem, 3vw, 2.5rem) 5rem;
        }}

        [data-testid="stMarkdownContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stForm"] {{
            min-width: 0;
            overflow-wrap: anywhere;
        }}

        .glass-card,
        .empty-card,
        .core-entry,
        div[data-testid="stMetric"],
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stForm"] {{
            border: 1px solid var(--border);
            background: var(--surface);
            box-shadow: var(--shadow-soft);
            backdrop-filter: blur(var(--glass-blur));
            -webkit-backdrop-filter: blur(var(--glass-blur));
        }}

        .glass-card,
        .empty-card {{
            border-radius: var(--card-radius);
            padding: 1.2rem 1.3rem;
        }}

        .auth-hero {{
            margin: 0 auto 1.6rem;
            max-width: 780px;
            padding: clamp(1.5rem, 5vw, 2.6rem);
            border: 1px solid rgba(255, 255, 255, .42);
            border-radius: 28px;
            color: white;
            background:
                linear-gradient(135deg, rgba(11, 95, 89, .96), rgba(15, 118, 110, .88)),
                radial-gradient(circle at top right, #7dd3c7, transparent 55%);
            box-shadow: var(--shadow-lift);
            text-align: center;
        }}

        .auth-hero h1 {{
            color: white; margin: .45rem 0 .6rem;
            font-size: clamp(2rem, 5vw, 3rem);
        }}

        .auth-hero p {{
            margin: 0; color: rgba(255, 255, 255, .9); font-size: 1.05rem;
        }}

        .auth-kicker,
        .task-time-badge,
        .status-pill {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            font-size: .82rem;
            font-weight: 800;
            letter-spacing: .02em;
        }}

        .auth-kicker {{
            padding: .3rem .75rem; border: 1px solid rgba(255, 255, 255, .4);
            letter-spacing: .08em;
        }}

        .section-heading {{
            margin: 1.7rem 0 .7rem; color: var(--ink);
            font-size: 1.2rem; font-weight: 800;
        }}

        .page-header {{ margin-bottom: 1.25rem; }}

        .page-header h1 {{
            margin: .2rem 0 .45rem; color: var(--ink); letter-spacing: -.025em;
        }}

        .page-header p {{
            max-width: 46rem; margin: 0; color: var(--muted); font-size: 1rem;
        }}

        .page-eyebrow {{
            color: var(--primary); font-size: .76rem; font-weight: 850;
            letter-spacing: .1em; text-transform: uppercase;
        }}

        .empty-card {{ margin-top: 1rem; }}

        .core-entry {{ margin-bottom: .7rem; padding: .85rem .95rem; border-radius: 16px; }}

        div[data-testid="stMetric"] {{ min-height: 116px; padding: 1rem 1.1rem; border-radius: 18px; }}
        .growth-dashboard-grid, .st-key-growth-dashboard-grid [data-testid="stHorizontalBlock"] {{ display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8rem !important; }}
        .growth-dashboard-grid > *, .st-key-growth-dashboard-grid [data-testid="stColumn"] {{ width: 100% !important; min-width: 0 !important; }}
        .growth-dashboard-grid .glass-card {{ margin: 0; }}

        .stButton > button,
        .stFormSubmitButton > button,
        [data-testid="stPageLink"] a {{
            min-height: var(--touch-target);
            border-radius: 14px;
            font-weight: 750;
            transition:
                transform .18s ease,
                box-shadow .18s ease,
                border-color .18s ease;
        }}

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 10px 24px rgba(15, 118, 110, .12);
        }}

        .current-user {{ margin: .4rem 0 .2rem; color: var(--muted); font-size: .82rem; font-weight: 700; text-align: right; }}

        .task-time-badge,
        .status-pill {{
            margin: .15rem 0 .45rem;
            padding: .3rem .72rem;
            color: var(--primary-dark);
            background: rgba(159, 226, 216, .34);
            white-space: nowrap;
        }}

        .status-pill--success {{
            color: #0B5F59; background: rgba(159, 226, 216, .42);
        }}

        .status-pill--warning {{
            color: #8A4B13; background: rgba(247, 210, 164, .48);
        }}

        .status-pill--danger {{
            color: #9F2D2D; background: rgba(248, 180, 180, .42);
        }}

        .st-key-mobile_bottom_navigation {{ display: none; }}

        @media (max-width: 1024px) {{
            .block-container {{
                width: 100%; padding-inline: 1.25rem;
            }}
        }}

        @media (min-width: 1366px) {{
            .block-container {{ padding-top: 2.25rem; padding-bottom: 4rem; }}
            .section-heading {{ margin-top: 2rem; }}
        }}

        @media (max-width: 768px) {{
            :root {{ --glass-blur: 10px; }}

            .growth-dashboard-grid, .st-key-growth-dashboard-grid [data-testid="stHorizontalBlock"] {{ grid-template-columns: 1fr; }}

            .block-container {{
                width: 100%;
                padding:
                    1rem .9rem
                    calc(5.5rem + env(safe-area-inset-bottom));
            }}

            [data-testid="stSidebar"] {{ display: none; }}

            .st-key-mobile_bottom_navigation {{
                position: fixed;
                z-index: 999;
                right: .6rem;
                bottom: calc(.55rem + env(safe-area-inset-bottom));
                left: .6rem;
                display: block;
                padding: .45rem;
                border: 1px solid var(--border);
                border-radius: 20px;
                background: var(--surface-strong);
                box-shadow: 0 14px 40px rgba(16, 42, 46, .18);
                backdrop-filter: blur(var(--glass-blur));
                -webkit-backdrop-filter: blur(var(--glass-blur));
            }}

            .st-key-mobile_bottom_navigation [data-testid="stHorizontalBlock"] {{
                gap: .25rem !important;
            }}
            .st-key-mobile_bottom_navigation [data-testid="stColumn"] {{ min-width: 0 !important; flex: 1 1 0 !important; }}
            .st-key-mobile_bottom_navigation [data-testid="stPageLink"] a,
            .st-key-mobile_bottom_navigation .stPopover > button {{
                min-height: 48px;
                padding: .35rem .25rem;
                font-size: .76rem;
            }}

            h1 {{ font-size: 1.7rem !important; line-height: 1.24 !important; }}

            h2 {{ font-size: 1.32rem !important; }}

            h3 {{ font-size: 1.08rem !important; }}

            .section-heading {{
                margin-top: 1.2rem; font-size: 1.08rem;
            }}

            .current-user {{ text-align: left; }}

            [data-testid="stHorizontalBlock"] {{
                gap: .7rem !important;
            }}

            div[data-testid="stMetric"] {{
                min-height: 104px; padding: .8rem .9rem;
            }}

            .stButton > button,
            .stFormSubmitButton > button,
            [data-testid="stPageLink"] a {{
                min-height: 44px;
            }}

            [data-testid="stDataFrame"],
            [data-testid="stTable"] {{
                max-width: 100%;
                overflow-x: auto;
            }}

            .auth-hero {{ border-radius: 22px; }}
        }}

        @media (max-width: 430px) {{
            .growth-dashboard-grid, .st-key-growth-dashboard-grid [data-testid="stHorizontalBlock"] {{ gap: .65rem !important; }}

            [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; }}
            [data-testid="stColumn"] {{ min-width: min(100%, 9rem) !important; }}
        }}

        @media (max-width: 375px) {{
            .block-container {{ padding-inline: .75rem; }}
            .st-key-mobile_bottom_navigation {{ right: .4rem; left: .4rem; }}
            .st-key-mobile_bottom_navigation [data-testid="stPageLink"] a {{
                font-size: .7rem;
            }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            *,
            *::before,
            *::after {{
                scroll-behavior: auto !important; transition-duration: .01ms !important;
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
            }}
        }}
        footer {{ visibility: hidden; }}
        </style>
        """
    ).strip()
