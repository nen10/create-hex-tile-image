# Hex Image Skill Design

## 目的

この設計は、agent が生成した画像を後続 pipeline で使える hex tile asset に変換し、さらに Godot 向け tile atlas としてまとめるための skill と tool 群を定義する。

既存の `hex-tile-cropper/index.html` は人間が画像を見ながら crop する PoC として扱う。agent 向けには、ドラッグ操作ではなく、再現可能な CLI、manifest、sidecar metadata を成果物の中心にする。

## 要件の分離

### Skill として記述する要件

- agent が画像生成後に必ず crop 前の source image を残す。
- downstream format から `orientation`、出力サイズ、出力先 directory を判断する。
- crop 位置は高レベル指定から始める。
  - `center`: 中央 crop。
  - `full-fit`: 画像全体をできるだけ残す。
  - `focus`: 顔や主題などの焦点座標を中心に crop。
- batch crop では同じ orientation と size の成果物を同じ directory にまとめる。
- atlas 化では orientation、size、metadata が合わない PNG を混ぜない。
- Godot 向け atlas は、canvas の width と height の差が小さくなる grid を選ぶ。

### 開発項目として記述する要件

- `SKILL.md` を含む skill directory を作成する。
- crop、batch crop、atlas pack を別 tool として実装する。
- 各 tile PNG に `.hex.json` sidecar を作成する。
- batch manifest と atlas manifest を JSON で作成する。
- preview overlay を任意出力できるようにする。
- sample pipeline を実行し、source retention、crop、batch、atlas、manifest が成立することを検証する。

## 成果物形式

推奨 directory layout:

```text
<asset-work-dir>/
  sources/
    <generated-source>.png
  tiles/
    <orientation>/
      <width>x<height>/
        <tile-name>.png
        <tile-name>.hex.json
  previews/
    <orientation>/
      <width>x<height>/
        <tile-name>-overlay.png
  manifests/
    batch-<orientation>-<width>x<height>.json
  atlases/
    <orientation>/
      <width>x<height>/
        atlas.png
        atlas.json
```

### Source image

Source image は crop 前の生成画像で、必ず `sources/` に残す。後で crop 条件を変えたり、別 orientation を作るための再実行点になる。

### Tile PNG

Tile PNG は透明背景 RGBA の hex-shaped image。指定 canvas サイズの中に正六角形を配置する。canvas と hex bounding box が完全一致しない場合、余白は透明にする。

### Tile sidecar

各 tile PNG と同じ basename で `.hex.json` を置く。

```json
{
  "role": "hex_tile",
  "tool": "hex_crop.py",
  "input": "sources/source.png",
  "output": "tiles/pointy/512x591/source-pointy-512x591-hex.png",
  "orientation": "pointy",
  "outputSize": { "width": 512, "height": 591 },
  "selection": {
    "mode": "focus",
    "x": 120,
    "y": 80,
    "w": 900,
    "h": 1039
  },
  "hexBox": { "x": 0, "y": 0, "w": 512, "h": 591 },
  "transparentMargin": { "x": 0, "y": 0 },
  "warnings": []
}
```

Sidecar は atlas tool が混入防止に使う authoritative metadata とする。

### Batch manifest

Batch manifest は batch crop の全体結果を記録する。

```json
{
  "role": "hex_tile_batch",
  "orientation": "pointy",
  "outputSize": { "width": 512, "height": 591 },
  "records": [
    {
      "input": "sources/a.png",
      "output": "tiles/pointy/512x591/a-pointy-512x591-hex.png",
      "sidecar": "tiles/pointy/512x591/a-pointy-512x591-hex.hex.json"
    }
  ],
  "skipped": []
}
```

### Atlas PNG and atlas manifest

Atlas PNG は uniform tile size の grid。Godot では tile size と atlas coordinates を使って取り込む。

```json
{
  "role": "hex_tile_atlas",
  "orientation": "pointy",
  "tileSize": { "width": 512, "height": 591 },
  "atlasSize": { "width": 1536, "height": 1182 },
  "columns": 3,
  "rows": 2,
  "entries": [
    {
      "name": "a-pointy-512x591-hex",
      "source": "tiles/pointy/512x591/a-pointy-512x591-hex.png",
      "x": 0,
      "y": 0,
      "w": 512,
      "h": 591,
      "col": 0,
      "row": 0
    }
  ],
  "skipped": []
}
```

## Tool 構成

### `hex_crop.py`

単一画像を hex tile PNG に変換する。source image、output PNG、sidecar JSON、preview overlay を作る。

主な指定:

- `--orientation pointy|flat`
- `--size WIDTHxHEIGHT`
- `--selection center|full-fit|focus`
- `--fill 0.82`
- `--focus X,Y`
- `--focus-units px|normalized`
- `--preview <path>`

### `hex_batch.py`

directory 内の画像を同じ format で batch crop する。出力は統一された tile directory と batch manifest。

Spec JSON を渡すと、画像ごとに `selection`、`focus`、`fill`、`outputName` を上書きできる。

### `hex_atlas.py`

cropped tile directory を atlas PNG にまとめる。`.hex.json` sidecar があり、orientation と size が一致する PNG だけを採用する。grid は `abs(atlas_width - atlas_height)` が小さくなる候補を選ぶ。

## Pipeline

1. 画像を生成し、crop 前 source を `sources/` に保存する。
2. downstream format から orientation と size を決める。
3. まず `center` または `full-fit` で crop し、preview overlay を確認する。
4. 主題がずれる場合は `focus` を使い、normalized coordinate で再 crop する。
5. 同じ format の tile を batch directory に集約する。
6. `hex_atlas.py` で atlas を作る。
7. manifest の `skipped` と `warnings` を確認する。

## 完了条件

- `skills/create-hex-tile-image/SKILL.md` があり、skill の workflow が記述されている。
- crop、batch、atlas の scripts が実行できる。
- source image、tile PNG、tile sidecar、batch manifest、atlas PNG、atlas manifest が実際に生成される。
- atlas tool が sidecar を使って incompatible file を混ぜない。
- sample pipeline の実行結果で上記成果物を確認できる。
