#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from hexlib import IMAGE_EXTENSIONS, resolve_size, write_json

try:
    from PIL import Image
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required for atlas packing.") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pack matching hex tile PNGs into a near-square atlas.")
    parser.add_argument("input_dir", type=Path, help="Directory containing cropped tile PNGs")
    parser.add_argument("--out", required=True, type=Path, help="Output atlas PNG")
    parser.add_argument("--manifest", type=Path, help="Output atlas manifest JSON")
    parser.add_argument("--orientation", choices=["pointy", "flat"], required=True)
    parser.add_argument("--long-side", type=int, help="Longer tile side in px; must match the tiles (recommended)")
    parser.add_argument("--size", help="Exact tile size as WIDTHxHEIGHT (alternative to --long-side)")
    parser.add_argument("--pattern", default="*.png")
    parser.add_argument("--strict", action="store_true", help="Fail if incompatible files are found")
    parser.add_argument("--json", action="store_true")
    return parser


def choose_grid(count: int, tile_w: int, tile_h: int) -> tuple[int, int]:
    best: tuple[int, int, int, int, int] | None = None
    sqrt = math.floor(math.sqrt(count))
    find_range = math.ceil((2 - math.sqrt(3)) * count)
    for cols in range(max(1, sqrt - find_range), min(sqrt + 1 + find_range + 1, count + 1)):
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


def read_sidecar(path: Path) -> dict[str, Any] | None:
    sidecar = path.with_suffix(".hex.json")
    if not sidecar.exists():
        return None
    return json.loads(sidecar.read_text(encoding="utf-8"))


def main() -> int:
    args = build_parser().parse_args()
    tile_w, tile_h = resolve_size(args.size, args.long_side, args.orientation)
    skipped: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    for path in sorted(args.input_dir.glob(args.pattern)):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        sidecar = read_sidecar(path)
        if sidecar is None:
            skipped.append({"input": str(path), "reason": "missing .hex.json sidecar"})
            continue
        if sidecar.get("role") != "hex_tile":
            skipped.append({"input": str(path), "reason": "sidecar role is not hex_tile"})
            continue
        if sidecar.get("orientation") != args.orientation:
            skipped.append({"input": str(path), "reason": "orientation mismatch"})
            continue
        output_size = sidecar.get("outputSize", {})
        if output_size.get("width") != tile_w or output_size.get("height") != tile_h:
            skipped.append({"input": str(path), "reason": "tile size mismatch"})
            continue
        with Image.open(path) as image:
            if image.size != (tile_w, tile_h):
                skipped.append({"input": str(path), "reason": "PNG dimensions do not match requested tile size"})
                continue
        candidates.append({"path": path, "sidecar": sidecar})

    if args.strict and skipped:
        manifest = {
            "role": "hex_tile_atlas",
            "tool": "hex_atlas.py",
            "orientation": args.orientation,
            "tileSize": {"width": tile_w, "height": tile_h},
            "entries": [],
            "skipped": skipped,
            "error": "strict mode rejected incompatible files",
        }
        if args.manifest:
            write_json(args.manifest, manifest)
        if args.json:
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 2

    if not candidates:
        raise SystemExit("no compatible hex tile PNGs found")

    cols, rows = choose_grid(len(candidates), tile_w, tile_h)
    atlas = Image.new("RGBA", (cols * tile_w, rows * tile_h), (0, 0, 0, 0))
    entries: list[dict[str, Any]] = []

    for index, candidate in enumerate(candidates):
        path = candidate["path"]
        col = index % cols
        row = index // cols
        x = col * tile_w
        y = row * tile_h
        with Image.open(path) as image:
            atlas.alpha_composite(image.convert("RGBA"), (x, y))
        entries.append(
            {
                "name": path.stem,
                "source": str(path),
                "sidecar": str(path.with_suffix(".hex.json")),
                "x": x,
                "y": y,
                "w": tile_w,
                "h": tile_h,
                "col": col,
                "row": row,
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(args.out)
    manifest_path = args.manifest or args.out.with_suffix(".json")
    manifest = {
        "role": "hex_tile_atlas",
        "tool": "hex_atlas.py",
        "inputDirectory": str(args.input_dir),
        "output": str(args.out),
        "orientation": args.orientation,
        "tileSize": {"width": tile_w, "height": tile_h},
        "atlasSize": {"width": atlas.width, "height": atlas.height},
        "columns": cols,
        "rows": rows,
        "entries": entries,
        "skipped": skipped,
    }
    write_json(manifest_path, manifest)
    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
