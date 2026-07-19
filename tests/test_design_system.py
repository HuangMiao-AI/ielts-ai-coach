"""Behavioral contracts for the shared visual design system."""

from __future__ import annotations

import pytest

from ielts_ai_coach.ui import components
from ielts_ai_coach.ui.design_system import DESIGN_TOKENS, build_app_css


def test_design_tokens_define_readable_surfaces_and_touch_targets() -> None:
    """Shared tokens must encode the accessibility baseline once."""

    assert DESIGN_TOKENS["color_text"] == "#102A2E"
    assert DESIGN_TOKENS["color_surface"] == "rgba(255, 255, 255, 0.82)"
    assert DESIGN_TOKENS["touch_target_px"] >= 44
    assert DESIGN_TOKENS["content_max_px"] >= 1180


def test_app_css_covers_supported_viewports_and_safe_motion() -> None:
    """The CSS contract must cover every required viewport and motion mode."""

    css = build_app_css()

    for width in (375, 430, 768, 1024, 1366):
        assert str(width) in css
    assert "backdrop-filter" in css
    assert "env(safe-area-inset-bottom)" in css
    assert "prefers-reduced-motion: reduce" in css
    assert "min-height: 44px" in css
    assert "overflow-x: clip" not in css


def test_mobile_glass_reduces_blur_cost() -> None:
    """Narrow screens must use a cheaper blur than the desktop shell."""

    css = build_app_css()

    assert "--glass-blur: 18px" in css
    assert "--glass-blur: 10px" in css


def test_shared_components_escape_student_visible_html(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shared HTML components must not interpolate executable markup."""

    rendered: list[str] = []
    monkeypatch.setattr(
        components.st,
        "markdown",
        lambda body, **_: rendered.append(body),
    )

    components.render_page_header(
        "<script>alert(1)</script>",
        "安全说明",
        eyebrow="阅读",
    )
    components.render_status_pill("<img src=x onerror=alert(1)>", "success")

    html = "".join(rendered)
    assert "<script>" not in html
    assert "<img" not in html
    assert "&lt;script&gt;" in html
    assert "status-pill--success" in html


def test_status_pill_rejects_unknown_tone() -> None:
    """Component variants must stay inside the supported visual vocabulary."""

    with pytest.raises(ValueError, match="Unsupported status tone"):
        components.render_status_pill("状态", "neon")
