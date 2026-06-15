---
name: create-hex-tile-image
description: Create hex-shaped image tile assets. The real work is generating good source artwork with your image-generation tool and iterating on it until it matches the request; the bundled scripts then mechanically crop each image into a pointy-top or flat-top transparent hex PNG and pack matching tiles into a Godot-ready atlas. Use when an agent needs a set of themed hex tiles or a hex tile atlas. Do not draw the artwork procedurally (no Pillow/SVG/canvas art) — the scripts handle all geometry and sizing, so spend your effort on the images.
---

# Create Hex Tile Image

## Overview

This skill has two parts, and they are not equal:

1. **Generate the source images (this is the work).** Use your image-generation tool to create artwork that matches the request, and iterate until it actually looks right. This is where almost all of your effort goes.
2. **Run the pipeline (this is mechanical).** Three deterministic scripts crop each source into a transparent hex PNG and pack matching tiles into an atlas. They handle every geometry and sizing decision for you. Do not think hard here — just run them.

The most common failure is inverting this: treating generation as a checkbox and pouring effort into sizes, grids, and crop math. Don't. **Sizing is solved.** If you ever feel tempted to compute tile dimensions or draw tiles yourself, stop — that is a signal you are in the wrong part of the task.

## Generate Source Images

This is the heart of the skill. Take it seriously and iterate.

### Use the image-generation tool — never draw the art yourself

Create every source image with the image-generation tool available to you (e.g. Codex's image generation / Image 2.0, or the equivalent image model in your environment). 

**Hard rule:** do not synthesize the artwork with Pillow, SVG, HTML canvas, NumPy, or any procedural drawing code. Procedural gradients-and-shapes are not tile art, and "deterministic / reproducible" is not a reason to skip real generation — that requirement applies only to the crop and atlas scripts, never to the artwork. The only Pillow in this skill lives inside the crop/pack scripts. If you cannot reach an image-generation tool, say so and stop; do not substitute a procedural placeholder.

### Iterate: generate → look → regenerate

Treat generation as a loop, not a single shot:

1. Write a clear prompt that captures the theme, palette, and subject framing the request asks for. For a set, decide what makes the set coherent (shared style, lighting, color story) and what varies per tile.
2. Generate a **small first batch** (e.g. 3–4), not the full count.
3. **Look at each one and decide accept or reject.** Compare against the request — on-theme? consistent with the set? When you **accept** an image, deciding *how it will be cropped* is part of the judgment, so record that now:
   - **Whole image, centered** — if the picture reads well as a whole and its subject sits near the middle, a plain centered crop is enough. Use `--selection center` (or `--selection full-fit` to keep as much of the image as possible). Nothing extra to record.
   - **A specific region** — if the important part is off-center, or you want a particular subject or zoom level, note a good crop center and size now: a normalized focus point and how much of the image to keep. These become `--selection focus --focus X,Y --focus-units normalized` (with `--fill` controlling how much area is kept). Write them down per image so you can hand them to the crop step instead of re-deciding later.
4. Reject the rest and **regenerate with an improved prompt.** Iterate on the prompt and the imagery — never on the geometry.
5. Once the first batch is solid, generate the remaining images in the same style and apply the same accept/record/regenerate pass.

A good stopping point is "every accepted source clearly matches the request, the set hangs together, and each one has a crop decision (centered, or a recorded focus + size)," not "I have N files."

### Practical generation tips

- **Generate large and roughly square.** Produce sources well above the final tile size (e.g. 1024px or more on the long side). The crop script downscales; starting large keeps tiles crisp. You never need to match the source to the tile size.
- **Frame the subject with margin.** A regular hex crop trims the corners, so keep the key subject away from the edges. If a subject sits off-center, you can steer the crop later with `--selection focus`, but it is easier to fix in the prompt.
- **Save every source before cropping.** Write each generated image into a `sources/` directory and keep it. Sources are your re-run point for a different orientation, size, or crop without regenerating.

## Run the Pipeline (mechanical)

Once `sources/` holds artwork you are happy with, the rest is three commands. Pass `--long-side N` and let the scripts derive everything else. You do **not** compute width/height, pick grids, or reason about geometry.

The scripts require Pillow. First try the active Python; if `python3 -c "import PIL"` fails in Codex Desktop, call `load_workspace_dependencies` and use the returned bundled Python executable.

### Size: just give the long side

The request usually states a long side (e.g. "long side 64px"). Pass it as `--long-side` and the script derives the canvas from the orientation:

- `pointy` is taller than wide → height is the long side (e.g. `--long-side 64` → 55×64).
- `flat` is wider than tall → width is the long side (e.g. `--long-side 64` → 64×55).

Do not compute these numbers yourself. (`--size WIDTHxHEIGHT` exists for the rare case you need an exact canvas.)

### Batch crop a folder of sources

```bash
python3 skills/create-hex-tile-image/scripts/hex_batch.py \
  work/sources \
  --out-dir work/tiles/pointy \
  --orientation pointy \
  --long-side 64 \
  --manifest work/manifests/batch-pointy.json \
  --json
```

For a different orientation, rerun the same command against the same `sources/` with `--orientation flat`.

The command above crops every source the same way (centered). To apply the **per-image crop decisions** you recorded while reviewing — focus point and fill for the images that needed a specific region — pass a `--spec` JSON; images not listed fall back to the centered default:

```json
{
  "defaults": { "selection": "center" },
  "items": [
    { "input": "reactor-core.png", "selection": "focus", "focus": [0.46, 0.38], "focusUnits": "normalized", "fill": 0.7 }
  ]
}
```

### Pack matching tiles into an atlas

```bash
python3 skills/create-hex-tile-image/scripts/hex_atlas.py \
  work/tiles/pointy \
  --out work/atlases/pointy/atlas.png \
  --manifest work/atlases/pointy/atlas.json \
  --orientation pointy \
  --long-side 64 \
  --json
```

The atlas tool reads each tile's `.hex.json` sidecar and automatically skips anything with the wrong orientation, wrong size, or missing metadata, and it picks the near-square grid for you. These deterministic guarantees are the scripts' job — you do not verify geometry by hand.

### When a single image or a custom crop is needed

Most runs only need batch + atlas. For a one-off tile, or to fine-tune framing on a specific image, `scripts/hex_crop.py` crops a single source and accepts `--selection center|full-fit|focus` (with `--focus X,Y --focus-units normalized`) and `--preview` to write an overlay showing the crop. Read `references/artifact-contract.md` for exact artifact paths and JSON fields.

## Completion Checks

Check the artwork first — that is what was actually requested:

- **Every source image matches the request** (theme, style, framing) and the set is coherent. State how many you regenerated to get there.
- Sources were generated with the image-generation tool, not drawn procedurally.

Then confirm the mechanical outputs:

- Source images still exist under `sources/`.
- Each tile PNG has a `.hex.json` sidecar, and the batch manifest `records` holds the expected tile count.
- The atlas manifest `entries` contains only matching tiles; inspect `skipped` / `warnings` and rerun only if they point to a real problem.
