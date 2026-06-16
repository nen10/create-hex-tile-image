#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path(__file__).resolve().parent
OUT_PNG = OUT_DIR / "choose-grid-blank-simulation.png"
OUT_CSV = OUT_DIR / "choose-grid-blank-simulation.csv"
MAX_COUNT = 256
TILE_SIZES = {
    "pointy long64": (55, 64),
    "flat long64": (64, 55),
}


@dataclass(frozen=True)
class GridMetrics:
    count: int
    cols: int
    rows: int
    tile_w: int
    tile_h: int

    @property
    def atlas_w(self) -> int:
        return self.cols * self.tile_w

    @property
    def atlas_h(self) -> int:
        return self.rows * self.tile_h

    @property
    def empty_cells(self) -> int:
        return self.cols * self.rows - self.count

    @property
    def empty_ratio(self) -> float:
        return self.empty_cells / (self.cols * self.rows)

    @property
    def blank_area_px(self) -> int:
        return self.empty_cells * self.tile_w * self.tile_h

    @property
    def aspect_delta_px(self) -> int:
        return abs(self.atlas_w - self.atlas_h)


def choose_original(count: int, tile_w: int, tile_h: int) -> tuple[int, int]:
    best: tuple[int, int, int, int, int] | None = None
    for cols in range(1, count + 1):
        rows = math.ceil(count / cols)
        atlas_w = cols * tile_w
        atlas_h = rows * tile_h
        empty = rows * cols - count
        score = (abs(atlas_w - atlas_h), empty, atlas_w * atlas_h, cols, rows)
        if best is None or score < best:
            best = score
    assert best is not None
    return best[3], best[4]


def choose_current(count: int, tile_w: int, tile_h: int) -> tuple[int, int]:
    best: tuple[float, int, int, int, int] | None = None
    sqrt = math.floor(math.sqrt(count))
    find_range = math.ceil((2 - math.sqrt(3)) * count)
    start = max(1, sqrt - find_range)
    stop = min(sqrt + 1 + find_range + 1, count + 1)
    for cols in range(start, stop):
        rows = math.ceil(count / cols)
        atlas_w = cols * tile_w
        atlas_h = rows * tile_h
        empty = rows * cols - count
        last_row_count = count % cols
        if last_row_count == 0:
            last_row_count = cols
        remain_rate = (cols - last_row_count) / cols
        second_order = remain_rate * (cols - math.sqrt(cols)) * tile_w
        score = (abs(atlas_w - atlas_h) + second_order, empty, atlas_w * atlas_h, cols, rows)
        if best is None or score < best:
            best = score
    assert best is not None
    return best[3], best[4]

def choose_board(count: int, tile_w: int, tile_h: int) -> tuple[int, int]:
    best: tuple[float, int, int, int, int] | None = None
    for cols in range(1, count + 1):
        rows = math.ceil(count / cols)
        atlas_w = cols * tile_w
        atlas_h = rows * tile_h
        empty = rows * cols - count
        last_row_count = count % cols
        if last_row_count == 0:
            last_row_count = cols
        remain_rate = (cols - last_row_count) / cols
        second_order = remain_rate * (cols - math.sqrt(cols)) * tile_w
        score = (abs(atlas_w - atlas_h) + second_order, empty, atlas_w * atlas_h, cols, rows)
        if best is None or score < best:
            best = score
    assert best is not None
    return best[3], best[4]


def metrics_for(count: int, tile_w: int, tile_h: int, chooser) -> GridMetrics:
    cols, rows = chooser(count, tile_w, tile_h)
    return GridMetrics(count=count, cols=cols, rows=rows, tile_w=tile_w, tile_h=tile_h)


def build_data() -> dict[str, dict[str, list[GridMetrics]]]:
    data: dict[str, dict[str, list[GridMetrics]]] = {}
    for label, (tile_w, tile_h) in TILE_SIZES.items():
        data[label] = {"original": [], "board": [], "current": []}
        for count in range(1, MAX_COUNT + 1):
            data[label]["original"].append(metrics_for(count, tile_w, tile_h, choose_original))
            data[label]["board"].append(metrics_for(count, tile_w, tile_h, choose_board))
            data[label]["current"].append(metrics_for(count, tile_w, tile_h, choose_current))
    return data


def write_csv(data: dict[str, dict[str, list[GridMetrics]]]) -> None:
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "orientation",
                "algorithm",
                "count",
                "cols",
                "rows",
                "atlas_width",
                "atlas_height",
                "aspect_delta_px",
                "empty_cells",
                "empty_ratio",
                "blank_area_px",
            ],
        )
        writer.writeheader()
        for orientation, algorithms in data.items():
            for algorithm, rows in algorithms.items():
                for row in rows:
                    writer.writerow(
                        {
                            "orientation": orientation,
                            "algorithm": algorithm,
                            "count": row.count,
                            "cols": row.cols,
                            "rows": row.rows,
                            "atlas_width": row.atlas_w,
                            "atlas_height": row.atlas_h,
                            "aspect_delta_px": row.aspect_delta_px,
                            "empty_cells": row.empty_cells,
                            "empty_ratio": f"{row.empty_ratio:.6f}",
                            "blank_area_px": row.blank_area_px,
                        }
                    )


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def nice_ticks(low: float, high: float, count: int = 5) -> list[float]:
    if high == low:
        return [low]
    span = high - low
    raw_step = span / max(1, count - 1)
    magnitude = 10 ** math.floor(math.log10(raw_step))
    normalized = raw_step / magnitude
    if normalized <= 1:
        step = magnitude
    elif normalized <= 2:
        step = 2 * magnitude
    elif normalized <= 5:
        step = 5 * magnitude
    else:
        step = 10 * magnitude
    start = math.floor(low / step) * step
    stop = math.ceil(high / step) * step
    ticks = []
    value = start
    while value <= stop + step * 0.5:
        ticks.append(value)
        value += step
    return ticks


def draw_chart(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    series: list[tuple[str, list[float], str, int]],
    y_label: str,
    y_min: float | None = None,
    y_max: float | None = None,
    zero_line: bool = False,
) -> None:
    x0, y0, x1, y1 = box
    title_font = load_font(25, bold=True)
    label_font = load_font(18)
    tick_font = load_font(15)
    grid_color = "#d5d8dc"
    axis_color = "#394150"
    text_color = "#1f2937"

    all_values = [value for _, values, _, _ in series for value in values]
    low = min(all_values) if y_min is None else y_min
    high = max(all_values) if y_max is None else y_max
    if zero_line:
        low = min(low, 0)
        high = max(high, 0)
    if low == high:
        low -= 1
        high += 1
    pad = (high - low) * 0.08
    low -= pad
    high += pad

    def map_x(count: int) -> float:
        return x0 + (count - 1) * (x1 - x0) / (MAX_COUNT - 1)

    def map_y(value: float) -> float:
        return y1 - (value - low) * (y1 - y0) / (high - low)

    draw.text((x0, y0 - 42), title, font=title_font, fill=text_color)
    draw.line((x0, y1, x1, y1), fill=axis_color, width=2)
    draw.line((x0, y0, x0, y1), fill=axis_color, width=2)

    for tick in nice_ticks(low, high):
        if tick < low or tick > high:
            continue
        y = map_y(tick)
        draw.line((x0, y, x1, y), fill=grid_color, width=1)
        label = f"{tick:.0f}" if abs(tick) >= 1 else f"{tick:.2f}"
        draw.text((x0 - 58, y - 9), label, font=tick_font, fill="#4b5563")

    for count in [1, 32, 64, 128, 192, 256]:
        x = map_x(count)
        color = "#8b5cf6" if count == 64 else grid_color
        width = 2 if count == 64 else 1
        draw.line((x, y0, x, y1), fill=color, width=width)
        draw.text((x - 13, y1 + 12), str(count), font=tick_font, fill="#4b5563")

    if zero_line and low < 0 < high:
        y = map_y(0)
        draw.line((x0, y, x1, y), fill="#111827", width=2)

    for _, values, color, width in series:
        points = [(map_x(index + 1), map_y(value)) for index, value in enumerate(values)]
        draw.line(points, fill=color, width=width, joint="curve")

    legend_x = x0 + 8
    legend_y = y0 + 8
    max_label_width = max((draw.textlength(label, font=label_font) for label, _, _, _ in series), default=0)
    draw.rectangle(
        (legend_x - 5, legend_y - 5, legend_x + 48 + max_label_width, legend_y + 28 * len(series) + 4),
        fill="#f8fafc",
    )
    for label, _, color, width in series:
        draw.line((legend_x, legend_y + 9, legend_x + 30, legend_y + 9), fill=color, width=width)
        draw.text((legend_x + 40, legend_y), label, font=label_font, fill=text_color)
        legend_y += 28

    draw.text((x0, y1 + 44), "tile count", font=label_font, fill=text_color)
    draw.text((x0 - 68, y0 - 24), y_label, font=label_font, fill=text_color)


def summary_lines(data: dict[str, dict[str, list[GridMetrics]]]) -> list[str]:
    lines = []
    for orientation, algorithms in data.items():
        original = algorithms["original"]
        current = algorithms["current"]
        deltas = [new.empty_cells - old.empty_cells for old, new in zip(original, current)]
        improved = sum(delta < 0 for delta in deltas)
        worse = sum(delta > 0 for delta in deltas)
        equal = MAX_COUNT - improved - worse
        best_improvement = min(deltas)
        worst_regression = max(deltas)
        old64 = original[63]
        new64 = current[63]
        lines.append(
            f"{orientation}: improved {improved}, worse {worse}, equal {equal}; "
            f"delta range {best_improvement:+d}..{worst_regression:+d}; "
            f"count64 {old64.cols}x{old64.rows}/{old64.empty_cells} -> {new64.cols}x{new64.rows}/{new64.empty_cells}"
        )
    return lines


def write_png(data: dict[str, dict[str, list[GridMetrics]]]) -> None:
    image = Image.new("RGB", (1800, 1190), "#f8fafc")
    draw = ImageDraw.Draw(image)
    title_font = load_font(36, bold=True)
    body_font = load_font(19)
    note_font = load_font(17)

    draw.text((70, 34), "choose_grid blank-space simulation", font=title_font, fill="#111827")
    draw.text(
        (70, 82),
        "original = abs(width-height), current = abs(width-height) + second_order. Range: 1..256 tiles, long side 64px.",
        font=body_font,
        fill="#334155",
    )
    draw.text((70, 108), "One empty cell is 3,520 px2 for both pointy 55x64 and flat 64x55.", font=note_font, fill="#64748b")

    boxes = {
        "pointy_empty": (92, 180, 835, 465),
        "flat_empty": (980, 180, 1723, 465),
        "pointy_delta": (92, 655, 835, 940),
        "flat_delta": (980, 655, 1723, 940),
    }
    colors = {"original": "#64748b", "current": "#0284c7", "delta": "#dc2626"}

    for orientation, empty_box, delta_box in [
        ("pointy long64", boxes["pointy_empty"], boxes["pointy_delta"]),
        ("flat long64", boxes["flat_empty"], boxes["flat_delta"]),
    ]:
        original = data[orientation]["board"]
        current = data[orientation]["current"]
        draw_chart(
            draw,
            empty_box,
            f"{orientation}: empty cells",
            [
                ("original", [row.empty_cells for row in original], colors["original"], 2),
                ("current", [row.empty_cells for row in current], colors["current"], 3),
            ],
            "cells",
            y_min=0,
        )
        delta_values = [new.empty_cells - old.empty_cells for old, new in zip(original, current)]
        draw_chart(
            draw,
            delta_box,
            f"{orientation}: current - original",
            [("negative = fewer blanks", delta_values, colors["delta"], 3)],
            "cells",
            zero_line=True,
        )

    y = 1028
    for line in summary_lines(data):
        draw.text((92, y), line, font=body_font, fill="#111827")
        y += 32
    draw.text((92, y + 8), f"CSV: {OUT_CSV.name}", font=note_font, fill="#64748b")

    image.save(OUT_PNG)


def main() -> int:
    data = build_data()
    write_csv(data)
    write_png(data)
    for line in summary_lines(data):
        print(line)
    print(f"wrote {OUT_PNG}")
    print(f"wrote {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
