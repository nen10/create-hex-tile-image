# Hex Scripts Spec

This document is a concise contract for the scripts bundled in `skills/create-hex-tile-image/scripts/`.

## Runtime

- Python 3.11+ is recommended.
- Pillow is required.
- In Codex Desktop, use the Python executable returned by `load_workspace_dependencies` when the system Python does not have Pillow.

## Shared Concepts

- `orientation`: `pointy` or `flat`.
- `size`: output canvas size as `WIDTHxHEIGHT`.
- `selection`: high-level crop strategy.
  - `center`: centered crop using `--fill`.
  - `full-fit`: largest crop matching the destination hex ratio.
  - `focus`: crop centered on `--focus X,Y`.
- `focus-units`: `px` or `normalized`.
- Tile sidecar: each tile PNG writes `<tile>.hex.json` unless disabled.

## Preview Overlay

Preview PNGs are diagnostic source overlays, not final assets.

- Area outside the selected crop rectangle is dimmed.
- Crop rectangle is shown with a yellow outline and light yellow fill.
- Hex crop area is shown with teal fill and a high-contrast white/teal outline.
- `focus` selections show a red crosshair at the requested focus point.

This makes the crop rectangle and final hex shape independently visible.

## `hex_crop.py`

Purpose: crop one source image into one transparent hex tile PNG.

Required:

```bash
python3 skills/create-hex-tile-image/scripts/hex_crop.py INPUT \
  --out OUTPUT.png \
  --orientation pointy \
  --size 512x591
```

Important options:

- `--selection center|full-fit|focus`
- `--fill 0.82`
- `--focus X,Y`
- `--focus-units px|normalized`
- `--anchor center|top|bottom|left|right|top-left|top-right|bottom-left|bottom-right`
- `--preview PREVIEW.png`
- `--manifest MANIFEST.json`
- `--no-sidecar`
- `--json`

Outputs:

- `OUTPUT.png`: RGBA PNG with transparent pixels outside the hex.
- `OUTPUT.hex.json`: tile sidecar metadata.
- Optional `PREVIEW.png`: source overlay preview.
- Optional manifest path, containing the same tile metadata.

## `hex_batch.py`

Purpose: crop a directory of source images into one uniform tile format.

Required:

```bash
python3 skills/create-hex-tile-image/scripts/hex_batch.py INPUT_DIR \
  --out-dir TILE_DIR \
  --orientation pointy \
  --size 512x591 \
  --manifest manifests/batch-pointy-512x591.json
```

Important options:

- `--selection center|full-fit|focus`
- `--preview-dir PREVIEW_DIR`
- `--pattern GLOB`
- `--spec SPEC.json`
- `--json`

Spec JSON can override per-image options:

```json
{
  "defaults": { "selection": "center", "fill": 0.82 },
  "items": [
    {
      "input": "portrait.png",
      "selection": "focus",
      "focus": [0.52, 0.38],
      "focusUnits": "normalized"
    }
  ]
}
```

Outputs:

- Uniform tile PNGs in `--out-dir`.
- `.hex.json` sidecars beside each tile.
- Optional preview PNGs in `--preview-dir`.
- Batch manifest with `records` and `skipped`.

## `hex_atlas.py`

Purpose: pack compatible cropped tile PNGs into a near-square atlas.

Required:

```bash
python3 skills/create-hex-tile-image/scripts/hex_atlas.py TILE_DIR \
  --out atlases/pointy/512x591/atlas.png \
  --manifest atlases/pointy/512x591/atlas.json \
  --orientation pointy \
  --size 512x591
```

Compatibility rules:

- PNG must have a matching `.hex.json` sidecar.
- Sidecar `role` must be `hex_tile`.
- Sidecar `orientation` must match `--orientation`.
- Sidecar `outputSize` and PNG dimensions must match `--size`.

Packing rule:

- Choose the grid that minimizes `abs(atlas_width - atlas_height)`.
- Use fewer empty cells as the next tie-breaker.

Options:

- `--pattern GLOB`
- `--strict`: return failure when incompatible files are present.
- `--json`

Outputs:

- `atlas.png`: RGBA atlas PNG.
- `atlas.json`: atlas manifest with `entries` and `skipped`.

## `make_sample_sources.py`

Purpose: create deterministic sample source images for local validation.

```bash
python3 skills/create-hex-tile-image/scripts/make_sample_sources.py \
  --out-dir outputs/skill-validation/sources \
  --count 4 \
  --size 960x768
```

This script is for validation only. It is not required by the production asset pipeline.
