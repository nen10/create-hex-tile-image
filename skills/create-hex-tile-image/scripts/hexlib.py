from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageOps
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by environment, not logic
    raise SystemExit(
        "Pillow is required. In Codex Desktop, call load_workspace_dependencies and use the "
        "bundled Python executable, or install Pillow in the active Python environment."
    ) from exc


SQRT3 = math.sqrt(3)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def parse_size(value: str) -> tuple[int, int]:
    text = value.lower().replace(" ", "")
    if "x" not in text:
        raise ValueError("size must use WIDTHxHEIGHT, for example 512x591")
    raw_w, raw_h = text.split("x", 1)
    width = int(raw_w)
    height = int(raw_h)
    if width < 16 or height < 16:
        raise ValueError("size must be at least 16x16")
    return width, height


def size_from_long_side(long_side: int, orientation: str) -> tuple[int, int]:
    """Return the (width, height) canvas whose longer side is ``long_side``.

    The canvas is sized so a regular hex fills it tightly (minimal transparent
    margin). pointy-top is taller than wide, so height is the long side;
    flat-top is wider than tall, so width is the long side.
    """
    if orientation not in {"pointy", "flat"}:
        raise ValueError("orientation must be pointy or flat")
    if long_side < 16:
        raise ValueError("long side must be at least 16")
    short_side = int(round(SQRT3 / 2 * long_side))
    if orientation == "pointy":
        return short_side, long_side
    return long_side, short_side


def resolve_size(size: str | None, long_side: int | None, orientation: str) -> tuple[int, int]:
    """Resolve the output canvas size from either --long-side or --size.

    --long-side is the recommended path: the caller passes one number and the
    width/height are derived from the orientation. --size remains for callers
    that need an exact canvas.
    """
    if long_side is not None and size is not None:
        raise ValueError("pass either --long-side or --size, not both")
    if long_side is not None:
        return size_from_long_side(long_side, orientation)
    if size is not None:
        return parse_size(size)
    raise ValueError("pass --long-side N (recommended) or --size WIDTHxHEIGHT")


def parse_pair(value: str) -> tuple[float, float]:
    text = value.replace(" ", "")
    if "," not in text:
        raise ValueError("pair values must use X,Y")
    raw_x, raw_y = text.split(",", 1)
    return float(raw_x), float(raw_y)


def round_number(value: float, digits: int = 4) -> float | int:
    rounded = round(float(value), digits)
    if rounded.is_integer():
        return int(rounded)
    return rounded


def round_rect(rect: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in rect.items():
        if isinstance(value, float):
            result[key] = round_number(value)
        else:
            result[key] = value
    return result


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def get_hex_geometry(width: int, height: int, orientation: str, regular: bool = True) -> dict[str, Any]:
    if orientation not in {"pointy", "flat"}:
        raise ValueError("orientation must be pointy or flat")

    hex_w = float(width)
    hex_h = float(height)
    side = None
    side_min = None
    side_max = None

    if regular:
        if orientation == "pointy":
            side = min(width / SQRT3, height / 2)
            hex_w = SQRT3 * side
            hex_h = 2 * side
        else:
            side = min(width / 2, height / SQRT3)
            hex_w = 2 * side
            hex_h = SQRT3 * side
        side_min = side
        side_max = side
    elif orientation == "pointy":
        diagonal_side = math.hypot(width / 2, height / 4)
        vertical_side = height / 2
        side = (diagonal_side + vertical_side) / 2
        side_min = min(diagonal_side, vertical_side)
        side_max = max(diagonal_side, vertical_side)
    else:
        horizontal_side = width / 2
        diagonal_side = math.hypot(width / 4, height / 2)
        side = (horizontal_side + diagonal_side) / 2
        side_min = min(horizontal_side, diagonal_side)
        side_max = max(horizontal_side, diagonal_side)

    return {
        "orientation": orientation,
        "regular": regular,
        "x": (width - hex_w) / 2,
        "y": (height - hex_h) / 2,
        "w": hex_w,
        "h": hex_h,
        "side": side,
        "sideMin": side_min,
        "sideMax": side_max,
    }


def hex_polygon(x: float, y: float, width: float, height: float, orientation: str) -> list[tuple[float, float]]:
    if orientation == "pointy":
        cx = x + width / 2
        return [
            (cx, y),
            (x + width, y + height * 0.25),
            (x + width, y + height * 0.75),
            (cx, y + height),
            (x, y + height * 0.75),
            (x, y + height * 0.25),
        ]

    cy = y + height / 2
    return [
        (x, cy),
        (x + width * 0.25, y),
        (x + width * 0.75, y),
        (x + width, cy),
        (x + width * 0.75, y + height),
        (x + width * 0.25, y + height),
    ]


def destination_ratio(width: int, height: int, orientation: str, regular: bool = True) -> float:
    hex_box = get_hex_geometry(width, height, orientation, regular)
    return float(hex_box["w"]) / float(hex_box["h"])


def clamp(value: float, min_value: float, max_value: float) -> float:
    return min(max(value, min_value), max_value)


def fit_rect_inside(
    image_w: int,
    image_h: int,
    ratio: float,
    fill: float,
) -> tuple[float, float]:
    fill = clamp(fill, 0.01, 1.0)
    max_w = image_w * fill
    max_h = image_h * fill
    width = max_w
    height = width / ratio
    if height > max_h:
        height = max_h
        width = height * ratio
    return max(1.0, width), max(1.0, height)


def anchor_center(anchor: str, image_w: int, image_h: int, sel_w: float, sel_h: float) -> tuple[float, float]:
    anchor = anchor.lower()
    x_map = {
        "left": sel_w / 2,
        "center": image_w / 2,
        "right": image_w - sel_w / 2,
    }
    y_map = {
        "top": sel_h / 2,
        "center": image_h / 2,
        "bottom": image_h - sel_h / 2,
    }

    parts = anchor.split("-")
    vertical = "center"
    horizontal = "center"
    for part in parts:
        if part in {"top", "bottom"}:
            vertical = part
        elif part in {"left", "right"}:
            horizontal = part
        elif part == "center":
            pass
        else:
            raise ValueError(f"unsupported anchor: {anchor}")
    return x_map[horizontal], y_map[vertical]


def clamp_selection(x: float, y: float, width: float, height: float, image_w: int, image_h: int) -> dict[str, float]:
    width = clamp(width, 1, image_w)
    height = clamp(height, 1, image_h)
    x = clamp(x, 0, image_w - width)
    y = clamp(y, 0, image_h - height)
    return {"x": x, "y": y, "w": width, "h": height}


def integer_sample_rect(selection: dict[str, float], image_w: int, image_h: int) -> tuple[int, int, int, int]:
    left = int(round(selection["x"]))
    top = int(round(selection["y"]))
    right = int(round(selection["x"] + selection["w"]))
    bottom = int(round(selection["y"] + selection["h"]))
    left = max(0, min(left, image_w - 1))
    top = max(0, min(top, image_h - 1))
    right = max(left + 1, min(right, image_w))
    bottom = max(top + 1, min(bottom, image_h))
    return left, top, right, bottom


def build_selection(
    image_size: tuple[int, int],
    output_size: tuple[int, int],
    orientation: str,
    mode: str = "center",
    fill: float = 0.82,
    focus: tuple[float, float] | None = None,
    focus_units: str = "px",
    anchor: str = "center",
    regular: bool = True,
) -> dict[str, Any]:
    image_w, image_h = image_size
    out_w, out_h = output_size
    if mode not in {"center", "full-fit", "focus"}:
        raise ValueError("selection mode must be center, full-fit, or focus")

    ratio = destination_ratio(out_w, out_h, orientation, regular)
    selection_fill = 1.0 if mode == "full-fit" else fill
    sel_w, sel_h = fit_rect_inside(image_w, image_h, ratio, selection_fill)

    if mode == "focus":
        if focus is None:
            raise ValueError("focus selection requires --focus X,Y")
        focus_x, focus_y = focus
        if focus_units == "normalized":
            focus_x *= image_w
            focus_y *= image_h
        elif focus_units != "px":
            raise ValueError("focus units must be px or normalized")
        center_x, center_y = focus_x, focus_y
    else:
        center_x, center_y = anchor_center(anchor, image_w, image_h, sel_w, sel_h)

    selection = clamp_selection(center_x - sel_w / 2, center_y - sel_h / 2, sel_w, sel_h, image_w, image_h)
    selection.update(
        {
            "mode": mode,
            "fill": selection_fill,
            "anchor": anchor,
        }
    )
    if focus is not None:
        selection["focus"] = {
            "x": focus[0],
            "y": focus[1],
            "units": focus_units,
        }
    return selection


def make_hex_mask(width: int, height: int, orientation: str) -> Image.Image:
    scale = 4 if max(width, height) <= 2048 else 2
    mask = Image.new("L", (width * scale, height * scale), 0)
    draw = ImageDraw.Draw(mask)
    points = [(x * scale, y * scale) for x, y in hex_polygon(0, 0, width, height, orientation)]
    draw.polygon(points, fill=255)
    return mask.resize((width, height), Image.Resampling.LANCZOS)


def output_hex_box(width: int, height: int, orientation: str, regular: bool = True) -> dict[str, int]:
    geom = get_hex_geometry(width, height, orientation, regular)
    x = int(round(geom["x"]))
    y = int(round(geom["y"]))
    hex_w = max(1, min(width - x, int(round(geom["w"]))))
    hex_h = max(1, min(height - y, int(round(geom["h"]))))
    return {"x": x, "y": y, "w": hex_w, "h": hex_h}


def render_hex_tile(
    input_path: Path,
    output_path: Path,
    orientation: str,
    size: tuple[int, int],
    selection_mode: str = "center",
    fill: float = 0.82,
    focus: tuple[float, float] | None = None,
    focus_units: str = "px",
    anchor: str = "center",
    preview_path: Path | None = None,
    regular: bool = True,
) -> dict[str, Any]:
    width, height = size
    source = ImageOps.exif_transpose(Image.open(input_path)).convert("RGBA")
    image_w, image_h = source.size
    selection = build_selection(
        (image_w, image_h),
        size,
        orientation,
        mode=selection_mode,
        fill=fill,
        focus=focus,
        focus_units=focus_units,
        anchor=anchor,
        regular=regular,
    )
    sample_rect = integer_sample_rect(selection, image_w, image_h)
    hex_box = output_hex_box(width, height, orientation, regular)

    cropped = source.crop(sample_rect)
    resized = cropped.resize((hex_box["w"], hex_box["h"]), Image.Resampling.LANCZOS)
    mask = make_hex_mask(hex_box["w"], hex_box["h"], orientation)

    tile = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    hex_layer = Image.new("RGBA", (hex_box["w"], hex_box["h"]), (0, 0, 0, 0))
    hex_layer.paste(resized, (0, 0), mask)
    tile.alpha_composite(hex_layer, (hex_box["x"], hex_box["y"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tile.save(output_path)

    if preview_path is not None:
        write_preview(source, preview_path, selection, orientation)

    transparent_margin = {
        "x": round_number((width - hex_box["w"]) / 2),
        "y": round_number((height - hex_box["h"]) / 2),
    }
    warnings: list[str] = []
    if transparent_margin["x"] or transparent_margin["y"]:
        warnings.append("regular hex does not fill the full canvas; transparent margins are present")

    return {
        "role": "hex_tile",
        "tool": "hex_crop.py",
        "input": str(input_path),
        "inputSha256": file_sha256(input_path),
        "inputSize": {"width": image_w, "height": image_h},
        "output": str(output_path),
        "orientation": orientation,
        "regular": regular,
        "outputSize": {"width": width, "height": height},
        "selection": round_rect(selection),
        "sampleRect": {
            "x": sample_rect[0],
            "y": sample_rect[1],
            "w": sample_rect[2] - sample_rect[0],
            "h": sample_rect[3] - sample_rect[1],
        },
        "hexBox": hex_box,
        "transparentMargin": transparent_margin,
        "preview": str(preview_path) if preview_path is not None else None,
        "warnings": warnings,
    }


def write_preview(source: Image.Image, preview_path: Path, selection: dict[str, Any], orientation: str) -> None:
    preview = source.copy()
    x = float(selection["x"])
    y = float(selection["y"])
    width = float(selection["w"])
    height = float(selection["h"])
    selection_box = (x, y, x + width, y + height)
    hex_points = hex_polygon(x, y, width, height, orientation)

    dim = Image.new("RGBA", preview.size, (0, 0, 0, 72))
    dim_draw = ImageDraw.Draw(dim)
    dim_draw.rectangle(selection_box, fill=(0, 0, 0, 0))
    preview = Image.alpha_composite(preview, dim)

    overlay = Image.new("RGBA", preview.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(selection_box, fill=(255, 214, 91, 26), outline=(255, 214, 91, 255), width=4)
    draw.polygon(hex_points, fill=(8, 127, 131, 46))
    draw.line(hex_points + [hex_points[0]], fill=(255, 255, 255, 255), width=8, joint="curve")
    draw.line(hex_points + [hex_points[0]], fill=(8, 127, 131, 255), width=4, joint="curve")

    focus = selection.get("focus")
    if isinstance(focus, dict):
        focus_x = float(focus.get("x", x + width / 2))
        focus_y = float(focus.get("y", y + height / 2))
        if focus.get("units") == "normalized":
            focus_x *= preview.width
            focus_y *= preview.height
        marker = max(8, min(preview.size) // 80)
        draw.line((focus_x - marker, focus_y, focus_x + marker, focus_y), fill=(255, 255, 255, 255), width=5)
        draw.line((focus_x, focus_y - marker, focus_x, focus_y + marker), fill=(255, 255, 255, 255), width=5)
        draw.line((focus_x - marker, focus_y, focus_x + marker, focus_y), fill=(196, 55, 55, 255), width=3)
        draw.line((focus_x, focus_y - marker, focus_x, focus_y + marker), fill=(196, 55, 55, 255), width=3)

    preview = Image.alpha_composite(preview, overlay)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview.save(preview_path)


def image_files(directory: Path, pattern: str = "*") -> list[Path]:
    return sorted(
        path
        for path in directory.glob(pattern)
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS and not path.name.endswith(".hex.png")
    )
