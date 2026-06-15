# Hex Scripts Spec

This document is a concise contract for the scripts bundled in `skills/create-hex-tile-image/scripts/`.

## Runtime

- Python 3.11+ is recommended.
- Pillow is required.
- In Codex Desktop, use the Python executable returned by `load_workspace_dependencies` when the system Python does not have Pillow.

## Shared Concepts

- `orientation`: `pointy` or `flat`.
- `long-side` (recommended): the longer tile side in px. The script derives the
  canvas from the orientation — `pointy` makes it the height, `flat` makes it the
  width — so callers never compute width/height. `--long-side 64` yields 55×64
  for `pointy` and 64×55 for `flat`.
- `size`: exact output canvas size as `WIDTHxHEIGHT`, for the rare case an exact
  canvas is required. Pass either `--long-side` or `--size`, not both.
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
  --long-side 64
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
  --long-side 64 \
  --manifest manifests/batch-pointy.json
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
  --out atlases/pointy/atlas.png \
  --manifest atlases/pointy/atlas.json \
  --orientation pointy \
  --long-side 64
```

Compatibility rules:

- PNG must have a matching `.hex.json` sidecar.
- Sidecar `role` must be `hex_tile`.
- Sidecar `orientation` must match `--orientation`.
- Sidecar `outputSize` and PNG dimensions must match the resolved tile size.

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

## `dev/make_validation_fixtures.py`

Purpose: draw deterministic geometric placeholders so the crop/atlas scripts have
inputs to self-test against. It lives in `dev/`, outside the skill, on purpose.

```bash
python3 dev/make_validation_fixtures.py \
  --out-dir outputs/skill-validation/sources \
  --count 4 \
  --size 960x768
```

This is a developer fixture, not part of the skill. It is **not** a way to make
tile artwork — real sources come from the image-generation tool. Never feed
procedurally drawn placeholders into a production atlas.
