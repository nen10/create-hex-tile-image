---
name: create-hex-tile-image
description: Generate and prepare hex-shaped image tile assets from source or AI-generated images. Use when Codex needs to retain pre-crop generated images, crop them into pointy-top or flat-top transparent PNG hex tiles, batch-process matching tile formats, or pack compatible cropped tiles into a near-square Godot-ready atlas with JSON manifests.
---

# Create Hex Tile Image

## Overview

Use this skill to turn generated or provided source images into reproducible hex tile assets. Keep the original generated image, crop it through deterministic scripts, write metadata sidecars, then optionally pack compatible tiles into an atlas.

## Workflow

1. Save every pre-crop generated image in a `sources/` directory before running any crop.
2. Decide the downstream format: `orientation` (`pointy` or `flat`) and output `size` (`WIDTHxHEIGHT`).
3. Crop one image with `scripts/hex_crop.py`, or crop a directory with `scripts/hex_batch.py`.
4. Review the manifest and optional preview overlay. If the subject is misplaced, rerun with `--selection focus --focus X,Y --focus-units normalized`.
5. Group cropped tiles by the same orientation and size.
6. Pack one group with `scripts/hex_atlas.py`. Rely on `.hex.json` sidecars to reject incompatible files.

Read `references/artifact-contract.md` when a downstream pipeline needs exact artifact paths or JSON fields.

## Python Runtime

The scripts require Pillow. First try the active Python:

```bash
python3 -c "import PIL"
```

If that fails in Codex Desktop, call `load_workspace_dependencies` and use the returned bundled Python executable.

## Single Crop

Use high-level selections first:

- `center`: default crop around the center.
- `full-fit`: keep as much of the source image as possible.
- `focus`: center the crop on a subject or face coordinate.

Example:

```bash
python3 skills/create-hex-tile-image/scripts/hex_crop.py \
  work/sources/tile-source.png \
  --out work/tiles/pointy/512x591/tile-source-pointy-512x591-hex.png \
  --orientation pointy \
  --size 512x591 \
  --selection center \
  --preview work/previews/pointy/512x591/tile-source-overlay.png \
  --json
```

For face-centered or subject-centered crops, estimate the focus point from the image and use normalized coordinates:

```bash
python3 skills/create-hex-tile-image/scripts/hex_crop.py \
  work/sources/portrait.png \
  --out work/tiles/pointy/512x591/portrait-pointy-512x591-hex.png \
  --orientation pointy \
  --size 512x591 \
  --selection focus \
  --focus 0.52,0.38 \
  --focus-units normalized \
  --preview work/previews/pointy/512x591/portrait-overlay.png
```

Each crop writes `<output>.hex.json` unless `--no-sidecar` is set.

## Batch Crop

Use batch crop after sources are already saved:

```bash
python3 skills/create-hex-tile-image/scripts/hex_batch.py \
  work/sources \
  --out-dir work/tiles/pointy/512x591 \
  --orientation pointy \
  --size 512x591 \
  --selection center \
  --preview-dir work/previews/pointy/512x591 \
  --manifest work/manifests/batch-pointy-512x591.json \
  --json
```

If individual images need different focus points, pass a spec JSON:

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

## Atlas Packing

Only pack a directory that contains cropped tiles from one orientation and size group. The atlas tool reads sidecars and skips files that are missing metadata or have mismatched size/orientation.

```bash
python3 skills/create-hex-tile-image/scripts/hex_atlas.py \
  work/tiles/pointy/512x591 \
  --out work/atlases/pointy/512x591/atlas.png \
  --manifest work/atlases/pointy/512x591/atlas.json \
  --orientation pointy \
  --size 512x591 \
  --json
```

Use `--strict` when mixed input should fail the run instead of producing a filtered atlas.

## Completion Checks

Before reporting completion:

- Confirm source images still exist under `sources/`.
- Confirm each tile PNG has a `.hex.json` sidecar.
- Confirm batch manifest `records` contains the expected tile count.
- Confirm atlas manifest `entries` contains only matching tile size and orientation.
- Inspect `warnings` and `skipped`; rerun with better focus or grouping if they indicate a real problem.
