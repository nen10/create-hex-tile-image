#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from hexlib import parse_pair, render_hex_tile, resolve_size, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crop one image into a transparent hex tile PNG.")
    parser.add_argument("input", type=Path, help="Source image path")
    parser.add_argument("--out", required=True, type=Path, help="Output PNG path")
    parser.add_argument("--orientation", choices=["pointy", "flat"], default="pointy")
    parser.add_argument("--long-side", type=int, help="Longer tile side in px; width/height derived from orientation (recommended)")
    parser.add_argument("--size", help="Exact output size as WIDTHxHEIGHT (alternative to --long-side)")
    parser.add_argument("--selection", choices=["center", "full-fit", "focus"], default="center")
    parser.add_argument("--fill", type=float, default=0.82, help="Selection fill ratio for center/focus modes")
    parser.add_argument("--focus", help="Focus point as X,Y for focus mode")
    parser.add_argument("--focus-units", choices=["px", "normalized"], default="px")
    parser.add_argument("--anchor", default="center", help="Anchor for center/full-fit, for example center, top, bottom-right")
    parser.add_argument("--preview", type=Path, help="Optional source overlay preview PNG")
    parser.add_argument("--manifest", type=Path, help="Optional manifest JSON path")
    parser.add_argument("--no-sidecar", action="store_true", help="Do not write <output>.hex.json")
    parser.add_argument("--no-regular", action="store_true", help="Allow a stretched hex to fill the canvas")
    parser.add_argument("--json", action="store_true", help="Print manifest JSON to stdout")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    focus = parse_pair(args.focus) if args.focus else None
    manifest = render_hex_tile(
        input_path=args.input,
        output_path=args.out,
        orientation=args.orientation,
        size=resolve_size(args.size, args.long_side, args.orientation),
        selection_mode=args.selection,
        fill=args.fill,
        focus=focus,
        focus_units=args.focus_units,
        anchor=args.anchor,
        preview_path=args.preview,
        regular=not args.no_regular,
    )

    if not args.no_sidecar:
        sidecar = args.out.with_suffix(".hex.json")
        write_json(sidecar, manifest)
        manifest["sidecar"] = str(sidecar)

    if args.manifest:
        write_json(args.manifest, manifest)

    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
