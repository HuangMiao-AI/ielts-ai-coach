"""PWA metadata and generated icon integrity tests."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from ielts_ai_coach.ui.pwa import build_pwa_head_markup


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = PROJECT_ROOT / "static"


def test_manifest_is_installable_without_claiming_offline_support() -> None:
    """Manifest must describe a standalone local shell and no service worker."""

    manifest = json.loads(
        (STATIC_ROOT / "manifest.webmanifest").read_text(encoding="utf-8")
    )

    assert manifest["name"] == "IELTS AI Coach"
    assert manifest["short_name"] == "IELTS Coach"
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["theme_color"] == "#0F766E"
    assert {icon["sizes"] for icon in manifest["icons"]} >= {
        "192x192",
        "512x512",
    }
    assert not (STATIC_ROOT / "service-worker.js").exists()


def test_generated_icons_have_exact_dimensions() -> None:
    """Every raster asset must match the dimensions encoded in its name."""

    expected = {
        "icon-192.png": (192, 192),
        "icon-512.png": (512, 512),
        "icon-maskable-512.png": (512, 512),
        "apple-touch-icon.png": (180, 180),
        "favicon-32.png": (32, 32),
    }
    for filename, size in expected.items():
        with Image.open(STATIC_ROOT / "icons" / filename) as image:
            assert image.size == size
            assert image.mode in {"RGB", "RGBA"}


def test_head_markup_references_local_manifest_and_accessibility_meta() -> None:
    """Installed metadata must use local static URLs and mobile-safe settings."""

    markup = build_pwa_head_markup()

    assert "/app/static/manifest.webmanifest" in markup
    assert "/app/static/icons/apple-touch-icon.png" in markup
    assert 'name="theme-color"' in markup
    assert 'name="apple-mobile-web-app-capable"' in markup
    assert "service-worker" not in markup


def test_streamlit_static_serving_is_enabled() -> None:
    """Streamlit must expose the repository static directory."""

    config = (PROJECT_ROOT / ".streamlit" / "config.toml").read_text(
        encoding="utf-8"
    )
    assert "enableStaticServing = true" in config
