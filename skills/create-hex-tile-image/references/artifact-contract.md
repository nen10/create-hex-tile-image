# Artifact Contract

Read this reference when integrating the skill output with another asset pipeline, checking manifests, or deciding where generated files should live.

## Directory Layout

Use this layout for repeatable work:

```text
<asset-work-dir>/
  sources/
  tiles/<orientation>/<width>x<height>/
  previews/<orientation>/<width>x<height>/
  manifests/
  atlases/<orientation>/<width>x<height>/
```

Keep generated source images in `sources/`. Do not overwrite them during crop iterations.

## Tile Sidecar

Each cropped PNG must have a `.hex.json` sidecar with the same basename:

```json
{
  "role": "hex_tile",
  "tool": "hex_crop.py",
  "input": "sources/source.png",
  "output": "tiles/pointy/512x591/source-pointy-512x591-hex.png",
  "orientation": "pointy",
  "outputSize": { "width": 512, "height": 591 },
  "selection": { "mode": "center", "x": 12, "y": 24, "w": 900, "h": 1039 },
  "hexBox": { "x": 0, "y": 0, "w": 512, "h": 591 },
  "transparentMargin": { "x": 0, "y": 0 },
  "warnings": []
}
```

Atlas tools treat this sidecar as authoritative. If a PNG has no sidecar, wrong orientation, or wrong size, skip it instead of mixing it into an atlas.

## Batch Manifest

`hex_batch.py` writes:

```json
{
  "role": "hex_tile_batch",
  "orientation": "pointy",
  "outputSize": { "width": 512, "height": 591 },
  "records": [],
  "skipped": []
}
```

Use `records` as the handoff list for atlas creation.

## Atlas Manifest

`hex_atlas.py` writes:

```json
{
  "role": "hex_tile_atlas",
  "orientation": "pointy",
  "tileSize": { "width": 512, "height": 591 },
  "atlasSize": { "width": 1024, "height": 1182 },
  "columns": 2,
  "rows": 2,
  "entries": [],
  "skipped": []
}
```

For Godot import, use `tileSize`, `columns`, `rows`, and each entry's `x`, `y`, `w`, and `h`.
