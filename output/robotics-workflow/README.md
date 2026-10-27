# Robotics workflow and video roles

All four panels are rendered from native assets. Cabinet geometry, UVs and PBR
bindings now come directly from the composed USD files used for the delivered
experiment videos. The previous synthetic dark wood / blue-gray edit palette,
handle substitutions and extra shelf were removed. No video frames or AI images
are used inside the workflow.

## Panels

1. **Retrieve from 400K+**: the yellow `crown_molding` cabinet is highlighted among
   eight multi-category dataset examples. This is a representative retrieval
   illustration, not an actual ranking of the nine objects.
2. **Edit**: the four actual video assets `seed_0000`, `seed_0001`, `strap_loop`
   and `t_bar`, with their native light wood finishes, proportions, handles and
   interiors. The retrieved cabinet and these four assets are displayed at a
   door angle of 0.98 radians (about 56° of the native 102° travel).
3. **Simulation training**: the original tall yellow cabinet in a flat-lit
   Workbench viewport, with light-gray robot parts and component contours.
   Frame 900 supplies the native left-Piper joint state and opening angle.
   Cabinet scale is 0.66, matching the simulation. There is no ground grid.
4. **Real-world deployment**: a shaded deployment schematic with a graphite
   right Piper and a yellow target cabinet made 28% shorter at the user's request.
   Radius and knob dimensions are preserved. The source frame-1800 forearm is
   translated down by the changed handle height (about 53 mm), maintaining contact.
   This is an illustration, not a recovered real-world pose or experimental image.
   Actual real trials remain in the video gallery immediately below it.

Both robot panels use the same orthographic scale, so the height difference is
visible. They illustrate the opening and closing phases of the same task, not
separate definitions of the training and deployment tasks. The idle arm is hidden;
proximal deployment-arm parts outside the focus area are hidden to avoid edge clutter.
The physical cabinet materials remain those of the video USD; simulation display
colors are adjusted only for the lighting-independent Workbench palette. Blender
studio lighting is not calibrated for pixel-identical colors to Isaac footage.

## Native appearance sources

- Composed assets: `/opt/isaacsim/isaac_route/assets/articulated/generated/round_cabinet_*.usd`.
- Material layers: corresponding `*_appearance.usda` files, including the final
  yellow coating and the recovered/repaired wood textures used in the videos.
- Video material report:
  `/opt/isaacsim/end/viewpoint_match_20261013/round_cabinet/material_import_report.json`.
- Original context: `MATERIAL_UPDATE.md` in that same source directory describes
  the material repairs already applied before the video delivery.
- Robot: `/opt/isaacsim/piper_official_isaac_asset_20260827/official_source/piper_with_gripper.urdf`;
  original Collada geometry, with a viewport or graphite presentation finish.
- Recorded state: `/opt/isaacsim/end/real_sim_fixed_camera_20261014/round_cabinet/round_cabinet_fixed_camera.jsonl`.
- Pool examples: existing exports in `public/models/dataset/`, whose origins are
  listed in `public/data/dataset.json`.

The Blender USD importer uses `MAKE_UNIQUE` for material names, preserving distinct
bindings across assets whose USD shaders share names. Imported surface names are
checked against the final video material report. Every referenced texture must
exist; paths and SHA-256 hashes are saved in `render-audit.json`. Source assets,
source textures and all 30 video encodings remain unchanged.

## Gallery roles

The user explicitly chose the current first simulation clip in each task as the
Displayed Retrieved asset, with the remaining clips labeled Edited 1–4. This
mapping is owner-designated for the page, not independently inferred provenance
from the manifest's `paper_representative` flag. Video order is unchanged.

| Task | Retrieved clip |
| --- | --- |
| Cabinet | `sim_crown_molding` |
| Folding chair | `sim_caret_fabric` |
| Double doors | `sim_seed2228` |
| Toaster | `sim_capsule_pill` |
| Folding ruler | `sim_seed0000` |

The explicit map lives in `scripts/robotics_roles.py`. It updates both the gallery
caption and enlarged-video title through `public/data/robotics.json`, and is also
called by `prepare_robotics.py` so re-encoding cannot silently remove these roles.
The Retrieved card gets a quiet dark border; no reordered or extra videos are added.

## Reproduce

Blender 4.2 LTS is required for the robot Collada importer. For each panel name
`retrieve`, `edit`, `train`, `deploy`, run on an idle GPU:

```bash
CUDA_VISIBLE_DEVICES=0 /tmp/blender-4.2.21-linux-x64/blender -b -t 8 \
  --python-exit-code 1 --python scripts/render_robotics_workflow.py -- retrieve
python scripts/compose_robotics_workflow.py
python scripts/robotics_roles.py
```

Panels are 1280 × 1280. Cycles uses OptiX, 128 samples and denoising; the simulation
panel uses Workbench with 32-sample antialiasing. Temporary PNGs, scenes and logs
live in `/tmp/rfw-workflow`. Pillow adds only headings, borders and connecting
arrows outside the rendered panels, using a sans-serif font.

Composition writes desktop (2854 × 742) and mobile (1394 × 1612) WebP images and
updates content hashes in their image/lightbox URLs to avoid stale cached images.
The mobile arrow preserves retrieve → edit → train → deploy reading order.
Enlarged pictures have no caption beneath them; accessible alt text remains.

The audit records native robot forward-kinematics agreement before the explicit
presentation translation. This verifies pose import, not physics validity of the
illustrative shorter target.
