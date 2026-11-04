"""Generate desktop icons for Tauri v2 bundle."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_base_icon(size: int = 1024) -> Image.Image:
    """Create a high-resolution base icon for ATEval Academic Revision."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded square with deep navy/indigo gradient
    corner_radius = int(size * 0.22)
    margin = int(size * 0.04)
    rect = [margin, margin, size - margin, size - margin]

    # Draw smooth rounded rectangle
    draw.rounded_rectangle(rect, radius=corner_radius, fill=(15, 23, 42, 255), outline=(56, 189, 248, 200), width=int(size * 0.015))

    # Inner decorative glow / subtle inner border
    inner_margin = int(size * 0.08)
    draw.rounded_rectangle(
        [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
        radius=int(corner_radius * 0.7),
        outline=(99, 102, 241, 120),
        width=int(size * 0.008),
    )

    # Stylized Academic "A" / Manuscript Quill Symbol
    # Draw a stylized open book / manuscript pages at the bottom half
    mid_x = size // 2
    book_top = int(size * 0.52)
    book_bottom = int(size * 0.78)
    book_left = int(size * 0.22)
    book_right = int(size * 0.78)

    # Left page
    draw.polygon(
        [
            (mid_x - 8, book_top + int(size * 0.05)),
            (book_left, book_top),
            (book_left, book_bottom),
            (mid_x - 8, book_bottom + int(size * 0.03)),
        ],
        fill=(30, 41, 59, 240),
        outline=(148, 163, 184, 180),
    )

    # Right page
    draw.polygon(
        [
            (mid_x + 8, book_top + int(size * 0.05)),
            (book_right, book_top),
            (book_right, book_bottom),
            (mid_x + 8, book_bottom + int(size * 0.03)),
        ],
        fill=(30, 41, 59, 240),
        outline=(148, 163, 184, 180),
    )

    # Page text lines (left page)
    line_color = (148, 163, 184, 160)
    for y_offset in [0.58, 0.63, 0.68, 0.73]:
        y = int(size * y_offset)
        draw.line(
            [(book_left + int(size * 0.05), y), (mid_x - int(size * 0.05), y + int(size * 0.01))],
            fill=line_color,
            width=int(size * 0.012),
        )

    # Page text lines (right page - with teal revision highlight!)
    for idx, y_offset in enumerate([0.58, 0.63, 0.68, 0.73]):
        y = int(size * y_offset)
        color = (56, 189, 248, 230) if idx == 1 else line_color
        draw.line(
            [(mid_x + int(size * 0.05), y + int(size * 0.01)), (book_right - int(size * 0.05), y)],
            fill=color,
            width=int(size * 0.012),
        )

    # Large prominent Greek alpha / modern "A" in upper center
    # Left leg
    draw.polygon(
        [
            (mid_x, int(size * 0.18)),
            (mid_x - int(size * 0.04), int(size * 0.18)),
            (mid_x - int(size * 0.20), int(size * 0.50)),
            (mid_x - int(size * 0.14), int(size * 0.50)),
        ],
        fill=(56, 189, 248, 255),
    )

    # Right leg
    draw.polygon(
        [
            (mid_x, int(size * 0.18)),
            (mid_x + int(size * 0.04), int(size * 0.18)),
            (mid_x + int(size * 0.20), int(size * 0.50)),
            (mid_x + int(size * 0.14), int(size * 0.50)),
        ],
        fill=(129, 140, 248, 255),
    )

    # Crossbar
    draw.rectangle(
        [mid_x - int(size * 0.12), int(size * 0.38), mid_x + int(size * 0.12), int(size * 0.42)],
        fill=(244, 114, 182, 240),
    )

    return img


def main() -> None:
    icons_dir = Path("src-tauri/icons")
    icons_dir.mkdir(parents=True, exist_ok=True)

    base = create_base_icon(1024)
    base.save(icons_dir / "icon.png")

    sizes = {
        "32x32.png": (32, 32),
        "128x128.png": (128, 128),
        "128x128@2x.png": (256, 256),
        "Square30x30Logo.png": (30, 30),
        "Square44x44Logo.png": (44, 44),
        "Square71x71Logo.png": (71, 71),
        "Square89x89Logo.png": (89, 89),
        "Square107x107Logo.png": (107, 107),
        "Square142x142Logo.png": (142, 142),
        "Square150x150Logo.png": (150, 150),
        "Square310x310Logo.png": (310, 310),
        "StoreLogo.png": (50, 50),
    }

    for name, dimensions in sizes.items():
        resized = base.resize(dimensions, Image.Resampling.LANCZOS)
        resized.save(icons_dir / name)

    # Save multi-size .ico
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base.save(icons_dir / "icon.ico", format="ICO", sizes=ico_sizes)

    # On macOS, build icon.icns using iconutil
    iconset_dir = icons_dir / "icon.iconset"
    iconset_dir.mkdir(exist_ok=True)
    icns_map = {
        "icon_16x16.png": (16, 16),
        "icon_16x16@2x.png": (32, 32),
        "icon_32x32.png": (32, 32),
        "icon_32x32@2x.png": (64, 64),
        "icon_128x128.png": (128, 128),
        "icon_128x128@2x.png": (256, 256),
        "icon_256x256.png": (256, 256),
        "icon_256x256@2x.png": (512, 512),
        "icon_512x512.png": (512, 512),
        "icon_512x512@2x.png": (1024, 1024),
    }
    for file_name, dims in icns_map.items():
        base.resize(dims, Image.Resampling.LANCZOS).save(iconset_dir / file_name)

    try:
        subprocess.run(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icons_dir / "icon.icns")], check=True)
        print("Generated icon.icns successfully.")
    except Exception as e:
        print(f"Warning: iconutil failed ({e}), saving fallback 512x512")
        base.resize((512, 512), Image.Resampling.LANCZOS).save(icons_dir / "icon.icns")

    print(f"All icons generated in {icons_dir}")


if __name__ == "__main__":
    main()
