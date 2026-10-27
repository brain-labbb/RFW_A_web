# Robotics workflow and video roles

All four panels are rendered from native assets. Cabinet geometry, UVs and PBR
bindings now come directly from the composed USD files used for the delivered
experiment videos. Native geometry and interiors are preserved. At the user’s request, the six-example
Edit panel now includes yellow, dark walnut and blue-gray finishes to illustrate material editing;
The added walnut and blue-gray finishes are diagram examples, not recorded trials. No video frames or AI images
are used inside the workflow.

## Panels

1. **Retrieve from 400K+**: the yellow `crown_molding` cabinet is highlighted among
   eight multi-category dataset examples. This is a representative retrieval
   illustration, not an actual ranking of the nine objects.
2. **Edit**: six half-open cabinets in two rows of three. The upper row uses
   native light-wood seed_0000, seed_0001 and strap_loop geometries to show
   proportion, handle and interior differences. The lower row uses yellow
   crown_molding, seed_0001 with a walnut-colored native wood texture, and t_bar
   with a blue-gray coating. All use the same view and metric display scale.
   These are illustrative method examples, not six recorded experimental trials;
   the video gallery remains unchanged. Door angle is 0.98 radians.
3. **Simulation training**: a shaded Cycles view with the dark Piper finish used
   in the simulation USD. Frame 900 supplies the native left-Piper joint state and
   opening angle. Cabinet scale remains 0.66, matching the simulation. The
   background is clean white, with no tabletop, floor grid or contact shadow.
4. **Real-world deployment**: a shaded deployment schematic with a dark right
   Piper and a yellow target cabinet made 28% shorter at the user's request.
   Radius and knob dimensions are preserved. The source frame-1800 forearm is
   translated down by the changed handle height (about 53 mm), maintaining contact.
   This is an illustration, not a recovered real-world pose or experimental image.
   Actual real trials remain in the video gallery immediately below it.

Both robot panels use the same orthographic scale and dark hardware color.
Simulation shows the taller cabinet and the left arm opening it against a clean
white background. Deployment shows the shorter cabinet, right arm closing it,
a higher opposite-side camera angle and a soft contact shadow. Neither has a
visible tabletop or floor grid. An invisible shadow catcher is used only for
deployment. The idle arm is hidden; proximal deployment-arm parts outside the
focus area are hidden. Both remain rendered illustrations.

### Color reproduction

The previous Workbench view overrode the robot with a light gray and flattened
its appearance. This has been removed. The original Collada geometry is retained,
but its white/gray material palette also differs from the experiment: inspection
of the composed Piper USD shows all 16 shaders use `diffuse_color_constant`
(0.018, 0.022, 0.028). Both panels use that dark finish in Cycles.

Simply importing the cabinet USD did not reproduce Isaac's displayed yellow:
the previous AgX/studio combination made it olive-brown. All four panels now use
Khronos PBR Neutral, exposure +0.5 and neutral lighting. The yellow coating alone
has an explicitly recorded Blender display calibration from linear RGB
(0.23, 0.19, 0.045) to (0.27, 0.265, 0.085), judged against the delivered cabinet
video. This is a rendering compensation; the source USD and videos are untouched.
We do not claim pixel-identical cross-renderer colors. The upper row retains native wood texture bindings/UVs; the walnut example
multiplies the native texture by a brown tint, preserving its UVs and grain. The five cabinet videos have two broad body appearances: one
yellow coating and four light-wood variants, with differences in wood grain,
handles, proportions and interiors. The walnut and blue-gray workflow
examples are separate illustrative material edits, not a claim about those videos.

## Native appearance sources

- Composed assets: `/opt/isaacsim/isaac_route/assets/articulated/generated/round_cabinet_*.usd`.
- Material layers: corresponding `*_appearance.usda` files, including the final
  yellow coating and the recovered/repaired wood textures used in the videos.
- Video material report:
  `/opt/isaacsim/end/viewpoint_match_20261013/round_cabinet/material_import_report.json`.
- Original context: `MATERIAL_UPDATE.md` in that same source directory describes
  the material repairs already applied before the video delivery.
- Robot: `/opt/isaacsim/piper_official_isaac_asset_20260827/official_source/piper_with_gripper.urdf`;
  original Collada geometry, with the dark diffuse color from the composed Isaac USD.
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

Panels are 1280 × 1280. All four panels use Cycles with OptiX, 128 samples and denoising. Temporary PNGs, scenes and logs
live in `/tmp/rfw-workflow`. Pillow adds only headings, borders and connecting
arrows outside the rendered panels, using a sans-serif font.

Composition writes desktop (2854 × 742) and mobile (1394 × 1612) WebP images and
updates content hashes in their image/lightbox URLs to avoid stale cached images.
The mobile arrow preserves retrieve → edit → train → deploy reading order.
Enlarged pictures have no caption beneath them; accessible alt text remains.

The audit records native robot forward-kinematics agreement before the explicit
presentation translation. This verifies pose import, not physics validity of the
illustrative shorter target.
