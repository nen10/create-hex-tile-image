#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from hexlib import image_files, parse_pair, render_hex_tile, resolve_size, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch crop source images into matching hex tile PNGs.")
    parser.add_argument("input_dir", type=Path, help="Directory containing source images")
    parser.add_argument("--out-dir", required=True, type=Path, help="Output tile directory")
    parser.add_argument("--orientation", choices=["pointy", "flat"], default="pointy")
    parser.add_argument("--long-side", type=int, help="Longer tile side in px; width/height derived from orientation (recommended)")
    parser.add_argument("--size", help="Exact output size as WIDTHxHEIGHT (alternative to --long-side)")
    parser.add_argument("--selection", choices=["center", "full-fit", "focus"], default="center")
    parser.add_argument("--fill", type=float, default=0.82)
    parser.add_argument("--focus", help="Default focus point as X,Y")
    parser.add_argument("--focus-units", choices=["px", "normalized"], default="px")
    parser.add_argument("--anchor", default="center")
    parser.add_argument("--pattern", default="*", help="Glob pattern within input_dir")
    parser.add_argument("--preview-dir", type=Path, help="Optional directory for overlay previews")
    parser.add_argument("--manifest", required=True, type=Path, help="Batch manifest JSON path")
    parser.add_argument("--spec", type=Path, help="Optional JSON spec with per-image overrides")
    parser.add_argument("--no-regular", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def load_spec(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"defaults": {}, "items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def spec_by_input(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in spec.get("items", []):
        if "input" not in item:
            continue
        result[str(item["input"])] = item
        result[Path(str(item["input"])).name] = item
    return result


def option_value(item: dict[str, Any], defaults: dict[str, Any], name: str, fallback: Any) -> Any:
    if name in item:
        return item[name]
    if name in defaults:
        return defaults[name]
    return fallback


def main() -> int:
    args = build_parser().parse_args()
    size = resolve_size(args.size, args.long_side, args.orientation)
    spec = load_spec(args.spec)
    defaults = spec.get("defaults", {})
    item_map = spec_by_input(spec)
    records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for input_path in image_files(args.input_dir, args.pattern):
        item = item_map.get(str(input_path), item_map.get(input_path.name, {}))
        selection = option_value(item, defaults, "selection", args.selection)
        fill = float(option_value(item, defaults, "fill", args.fill))
        focus_value = option_value(item, defaults, "focus", args.focus)
        focus_units = option_value(item, defaults, "focusUnits", args.focus_units)
        anchor = option_value(item, defaults, "anchor", args.anchor)
        output_name = option_value(
            item,
            defaults,
            "outputName",
            f"{input_path.stem}-{args.orientation}-{size[0]}x{size[1]}-hex.png",
        )
        focus = parse_pair(focus_value) if isinstance(focus_value, str) else None
        if isinstance(focus_value, list) and len(focus_value) == 2:
            focus = (float(focus_value[0]), float(focus_value[1]))

        output_path = args.out_dir / output_name
        preview_path = None
        if args.preview_dir:
            preview_path = args.preview_dir / f"{Path(output_name).stem}-overlay.png"

        try:
            tile_manifest = render_hex_tile(
                input_path=input_path,
                output_path=output_path,
                orientation=args.orientation,
                size=size,
                selection_mode=selection,
                fill=fill,
                focus=focus,
                focus_units=focus_units,
                anchor=anchor,
                preview_path=preview_path,
                regular=not args.no_regular,
            )
            sidecar = output_path.with_suffix(".hex.json")
            write_json(sidecar, tile_manifest)
            records.append(
                {
                    "input": str(input_path),
                    "output": str(output_path),
                    "sidecar": str(sidecar),
                    "preview": str(preview_path) if preview_path else None,
                    "selection": tile_manifest["selection"],
                    "warnings": tile_manifest["warnings"],
                }
            )
        except Exception as exc:  # keep batch work moving and record the bad item
            skipped.append({"input": str(input_path), "reason": str(exc)})

    batch_manifest = {
        "role": "hex_tile_batch",
        "tool": "hex_batch.py",
        "inputDirectory": str(args.input_dir),
        "outputDirectory": str(args.out_dir),
        "orientation": args.orientation,
        "outputSize": {"width": size[0], "height": size[1]},
        "records": records,
        "skipped": skipped,
    }
    write_json(args.manifest, batch_manifest)
    if args.json:
        print(json.dumps(batch_manifest, indent=2, ensure_ascii=False))
    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(main())
