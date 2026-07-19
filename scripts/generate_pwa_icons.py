"""Generate deterministic PWA PNG icons from the project palette."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "static" / "icons"


def _draw_icon(size: int, *, maskable: bool = False) -> Image.Image:
    """Draw one scalable book mark using only local Pillow primitives."""

    image = Image.new("RGBA", (size, size), "#0F766E")
    draw = ImageDraw.Draw(image)
    margin = int(size * (0.20 if maskable else 0.14))
    radius = int(size * 0.22)
    draw.rounded_rectangle(
        (0, 0, size - 1, size - 1),
        radius=radius,
        fill="#0F766E",
    )
    draw.ellipse(
        (
            int(size * 0.68),
            int(size * 0.12),
            int(size * 0.88),
            int(size * 0.32),
        ),
        fill="#E6A15A",
    )
    centre = size // 2
    top = int(size * 0.33)
    bottom = int(size * 0.76)
    draw.polygon(
        [
            (margin, top),
            (centre, int(size * 0.39)),
            (centre, bottom),
            (margin, int(size * 0.70)),
        ],
        fill="#FFF9EF",
    )
    draw.polygon(
        [
            (size - margin, top),
            (centre, int(size * 0.39)),
            (centre, bottom),
            (size - margin, int(size * 0.70)),
        ],
        fill="#F2EEE5",
    )
    width = max(2, int(size * 0.025))
    draw.line(
        (centre, int(size * 0.39), centre, bottom),
        fill="#0B5F59",
        width=width,
    )
    return image


def generate_icons() -> None:
    """Write every required deterministic raster icon."""

    OUTPUT.mkdir(parents=True, exist_ok=True)
    assets = {
        "icon-192.png": (192, False),
        "icon-512.png": (512, False),
        "icon-maskable-512.png": (512, True),
        "apple-touch-icon.png": (180, False),
        "favicon-32.png": (32, False),
    }
    for filename, (size, maskable) in assets.items():
        _draw_icon(size, maskable=maskable).save(
            OUTPUT / filename,
            format="PNG",
            optimize=True,
        )


if __name__ == "__main__":
    generate_icons()
