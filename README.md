# Hex Tile Convertor

Agent-oriented tools and a Codex skill for creating transparent hex tile PNGs from generated or provided images.

The original browser cropper in `hex-tile-cropper/` is a human-facing proof of concept. The publishable skill lives in `skills/create-hex-tile-image/` and exposes deterministic scripts for agent workflows.

## Skill Package

```text
skills/create-hex-tile-image/
  SKILL.md
  agents/openai.yaml
  references/artifact-contract.md
  scripts/hex_crop.py
  scripts/hex_batch.py
  scripts/hex_atlas.py
  scripts/hexlib.py
  scripts/make_sample_sources.py
```

The skill is prepared as a standalone folder with the required `SKILL.md`, UI metadata in `agents/openai.yaml`, bundled scripts, and a reference contract.

## What It Produces

Recommended artifact layout:

```text
work/
  sources/
  tiles/<orientation>/<width>x<height>/
  previews/<orientation>/<width>x<height>/
  manifests/
  atlases/<orientation>/<width>x<height>/
```

Key outputs:

- Source PNGs are retained before crop.
- Tile PNGs are transparent RGBA hex images.
- Each tile has a `.hex.json` sidecar.
- Batch and atlas manifests record what was produced or skipped.
- Atlas packing rejects mismatched size, orientation, or missing metadata.

## Runtime

The scripts require Pillow. If `python3 -c "import PIL"` fails, use the bundled Codex Desktop Python returned by `load_workspace_dependencies`.

## Quick Validation

```bash
PYTHON=${PYTHON:-python3}

$PYTHON skills/create-hex-tile-image/scripts/make_sample_sources.py \
  --out-dir outputs/skill-validation/sources \
  --count 4 \
  --size 960x768

$PYTHON skills/create-hex-tile-image/scripts/hex_batch.py \
  outputs/skill-validation/sources \
  --out-dir outputs/skill-validation/tiles/pointy/256x296 \
  --orientation pointy \
  --size 256x296 \
  --selection center \
  --preview-dir outputs/skill-validation/previews/pointy/256x296 \
  --manifest outputs/skill-validation/manifests/batch-pointy-256x296.json \
  --json

$PYTHON skills/create-hex-tile-image/scripts/hex_atlas.py \
  outputs/skill-validation/tiles/pointy/256x296 \
  --out outputs/skill-validation/atlases/pointy/256x296/atlas.png \
  --manifest outputs/skill-validation/atlases/pointy/256x296/atlas.json \
  --orientation pointy \
  --size 256x296 \
  --json
```

Generated validation artifacts go under `outputs/`, which is ignored by git.

## Documentation

- Design overview: `docs/design/hex-image-skill-design.md`
- Script contract: `docs/design/hex-scripts-spec.md`
- Skill artifact contract: `skills/create-hex-tile-image/references/artifact-contract.md`

## Publication Readiness

Current package status:

- Required skill metadata exists in `SKILL.md`.
- UI metadata exists in `agents/openai.yaml`.
- Runtime scripts are bundled inside the skill.
- Detailed long-form contract is split into `references/`.
- Root README and design docs describe usage and validation.

Before publishing, run a final validation pass:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py \
  skills/create-hex-tile-image
```

If the active Python lacks `yaml`, run the validator in an environment with PyYAML installed. In Codex Desktop, set `PYTHON` to the bundled Python executable returned by `load_workspace_dependencies` when the system Python does not include Pillow.
