#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required to generate sample sources.") from exc


PALETTES = [
    ("moss", (45, 82, 62), (158, 185, 116), (238, 205, 116)),
    ("shore", (39, 90, 121), (91, 172, 181), (238, 226, 186)),
    ("ember", (76, 42, 54), (190, 81, 50), (246, 169, 89)),
    ("snow", (72, 92, 105), (184, 207, 210), (250, 250, 240)),
]


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def create_source(path: Path, index: int, width: int, height: int) -> None:
    name, c0, c1, accent = PALETTES[index % len(PALETTES)]
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(lerp(c0[i], c1[i], t) for i in range(3))
        draw.line((0, y, width, y), fill=color)

    cx = width * (0.42 + 0.1 * (index % 3))
    cy = height * (0.38 + 0.08 * (index % 2))
    radius = min(width, height) * 0.22
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=accent)
    draw.ellipse((cx - radius * 0.45, cy - radius * 0.55, cx - radius * 0.22, cy - radius * 0.3), fill=(30, 37, 45))
    draw.ellipse((cx + radius * 0.22, cy - radius * 0.55, cx + radius * 0.45, cy - radius * 0.3), fill=(30, 37, 45))
    draw.arc((cx - radius * 0.42, cy - radius * 0.18, cx + radius * 0.42, cy + radius * 0.45), 10, 170, fill=(30, 37, 45), width=7)

    for step in range(0, width + height, 120):
        draw.line((step, 0, 0, step), fill=(255, 255, 255), width=3)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create deterministic sample source images for validating the hex pipeline.")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--size", default="960x768")
    args = parser.parse_args()
    width_text, height_text = args.size.lower().split("x", 1)
    width = int(width_text)
    height = int(height_text)
    for index in range(args.count):
        name = PALETTES[index % len(PALETTES)][0]
        create_source(args.out_dir / f"sample-{index + 1:02d}-{name}.png", index, width, height)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
