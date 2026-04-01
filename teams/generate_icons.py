"""
Generate Teams app icons (color.png 192x192 and outline.png 32x32).
Requires: pip install Pillow

Run: python teams/generate_icons.py
"""

from PIL import Image, ImageDraw
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BRAND_BLUE = (0, 120, 212)   # #0078d4
WHITE = (255, 255, 255)


def draw_lightning(draw: ImageDraw.ImageDraw, size: int, color, line_width: int = None) -> None:
    """Draw a simple lightning bolt centered in a square of `size` pixels."""
    if line_width is None:
        line_width = max(2, size // 20)
    s = size
    # Lightning bolt polygon (normalised to size)
    pts = [
        (s * 0.58, s * 0.08),   # top-right
        (s * 0.30, s * 0.52),   # mid-left
        (s * 0.50, s * 0.50),   # mid-center
        (s * 0.42, s * 0.92),   # bottom-left
        (s * 0.70, s * 0.48),   # mid-right
        (s * 0.50, s * 0.50),   # mid-center
    ]
    draw.polygon(pts, fill=color)


def make_color_icon(path: str) -> None:
    """192x192 full-color icon: blue background + white lightning bolt."""
    size = 192
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Rounded rectangle background
    radius = 36
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=BRAND_BLUE)
    draw_lightning(draw, size, WHITE)
    img.save(path, "PNG")
    print(f"Created {path}")


def make_outline_icon(path: str) -> None:
    """32x32 outline icon: transparent background + white lightning bolt."""
    size = 32
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw_lightning(draw, size, WHITE, line_width=1)
    img.save(path, "PNG")
    print(f"Created {path}")


if __name__ == "__main__":
    make_color_icon(os.path.join(SCRIPT_DIR, "color.png"))
    make_outline_icon(os.path.join(SCRIPT_DIR, "outline.png"))
    print("\nDone. Ready to zip:")
    print("  cd teams && zip -r ZetaIMA.zip manifest.json color.png outline.png")
