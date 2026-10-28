#!/usr/bin/env python3
"""Prepare directed-editing web assets.

Reads the five showcase specs' pipeline outputs from the arti-template
specific_editing pipeline, compresses every base/variant GLB for the browser
(meshopt + WebP textures), renders thumbnails from the pipeline's own
front_iso renders, and emits public/data/editing.json describing objects,
edit axes, and variants for the directed-editing workbench.

The source pipeline outputs are read-only. Tooling: gltf-transform CLI lives
in /tmp/gltf-tools (npm install @gltf-transform/cli). Run from the repo root:

    python3 scripts/prepare_editing.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

SRC = Path("/home/lyuyuanbo.lyb/PVA/arti-template/specific_editing/outputs/single_variable")
SPECS_SRC = Path("/home/lyuyuanbo.lyb/PVA/arti-template/specific_editing/specs/single_variable")
ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "public/models/editing"
MEDIA = ROOT / "public/media/editing"
DATA = ROOT / "public/data"
GLTF_TRANSFORM = Path("/tmp/gltf-tools/node_modules/.bin/gltf-transform")

SPECS = [
    ("cabinet_paper_showcase", "Side-hinged cabinet", "Doors, width, and finishes on a shared carcass."),
    ("fence", "Articulated cascade fence", "Panel modules, count, and materials on a folding chain."),
    ("ferris_wheel", "Ferris wheel", "Gondola modules, count, and wheel radius."),
    ("playground_chair_swing_carousel", "Chair-swing carousel", "Chair modules, count, and ring radius."),
    ("table_football", "Table football", "Support modules, rod count, and table length."),
]


def humanize(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return f"{value:g}"
    return str(value).replace("_", " ")


def short_label(variant: dict) -> str:
    label = variant["variant"]["label"]
    if ": " in label:
        return label.split(": ", 1)[1]
    return label


def value_readout(variant: dict, base_config: dict) -> str:
    requested = variant["requested_config"]
    diffs = []
    for key in sorted(set(requested) | set(base_config)):
        old, new = base_config.get(key), requested.get(key)
        if old != new:
            diffs.append(f"{key}: {json.dumps(old)} → {json.dumps(new)}")
    return "; ".join(diffs) or "base configuration"


def optimize_glb(src: Path, dst: Path) -> tuple[Path, int, int]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return dst, src.stat().st_size, dst.stat().st_size
    proc = subprocess.run(
        [
            str(GLTF_TRANSFORM), "optimize", str(src), str(dst),
            "--compress", "meshopt", "--texture-compress", "webp", "--texture-size", "1024",
        ],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gltf-transform failed for {src}:\n{proc.stdout}\n{proc.stderr}")
    return dst, src.stat().st_size, dst.stat().st_size


def main() -> int:
    if not GLTF_TRANSFORM.exists():
        sys.exit(f"gltf-transform missing: cd /tmp/gltf-tools && npm install @gltf-transform/cli")
    MODELS.mkdir(parents=True, exist_ok=True)
    MEDIA.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    jobs: list[tuple[Path, Path]] = []
    objects = []
    for spec_name, display, tagline in SPECS:
        out_dir = SRC / spec_name
        manifest = json.loads((out_dir / "manifest.json").read_text())
        spec = json.loads((SPECS_SRC / f"{spec_name}.json").read_text())
        base_config = manifest["base"]["config"]
        group_meta = manifest["comparison_groups"]  # group dir -> {kind, target}
        edit_labels = {(e["kind"], e["target"]): e.get("label", e["target"]) for e in spec["edits"]}

        jobs.append((out_dir / "base/scene.glb", MODELS / spec_name / "base.glb"))

        groups: dict[str, dict] = {}
        for v in manifest["variants"]:
            info = v["variant"]
            kind, target = info["kind"], info["target"]
            group_dir = next(g for g, meta in group_meta.items() if meta["kind"] == kind and meta["target"] == target)
            group = groups.setdefault(group_dir, {
                "group": group_dir, "kind": kind, "target": target,
                "label": edit_labels.get((kind, target), target),
                "variants": [],
            })
            jobs.append((out_dir / v["exports"]["scene_glb"], MODELS / spec_name / f"{info['variant_id']}.glb"))
            raw = info["value"]
            # Material overrides are not part of requested_config, so the
            # generic config diff is empty for them; the "from" side is always
            # the generator's default palette.
            if kind == "material":
                name = raw["name"] if isinstance(raw, dict) else str(raw)
                readout = f'{target}_material: default → "{name}"'
            else:
                readout = value_readout(v, base_config)
            variant = {
                "id": info["variant_id"],
                "label": short_label(v),
                "button": humanize(raw["name"] if isinstance(raw, dict) else raw),
                "readout": readout,
                "glb": f"models/editing/{spec_name}/{info['variant_id']}.glb",
            }
            if isinstance(raw, dict) and "rgba" in raw:
                variant["swatch"] = raw["rgba"]
            groups[group_dir]["variants"].append(variant)

        thumb_src = out_dir / "base/renders/closed__front_iso.png"
        img = Image.open(thumb_src).convert("RGB")
        thumb_w = 640
        img.resize((thumb_w, int(img.height * thumb_w / img.width)), Image.LANCZOS).save(
            MEDIA / f"{spec_name}.webp", "WEBP", quality=82
        )

        order = {"component": 0, "count": 1, "material": 2, "size": 3}
        axes = sorted(groups.values(), key=lambda g: (order.get(g["kind"], 9), g["group"]))
        objects.append({
            "id": spec_name,
            "name": display,
            "tagline": tagline,
            "generator": manifest["generator"],
            "thumbnail": f"media/editing/{spec_name}.webp",
            "baseGlb": f"models/editing/{spec_name}/base.glb",
            "baseReadout": "base configuration",
            "frame": manifest["shared_frame"],
            "axes": axes,
        })

    before = after = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for dst, src_bytes, dst_bytes in pool.map(lambda j: optimize_glb(*j), jobs):
            before += src_bytes
            after += dst_bytes
    (DATA / "editing.json").write_text(json.dumps({"objects": objects}, indent=1) + "\n")
    print(f"glb: {len(jobs)} files, {before/1e6:.1f} MB -> {after/1e6:.1f} MB")
    print(f"objects: {len(objects)}, variants: {sum(len(a['variants']) for o in objects for a in o['axes'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
