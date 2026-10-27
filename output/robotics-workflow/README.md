# Robotics workflow: native asset renders

The website uses four Blender-rendered panels, short headings and connecting
arrows. There are no AI-generated objects or extracted video frames in this
version. Desktop and mobile WebP assets are composed from the same four panels.

## Panel content

1. **Retrieve from 400K+**: eight multi-category dataset assets surround one
   highlighted round cabinet. Examples include a satellite, rover, paint roller,
   drawer cabinet, prosthetic limb, sewing machine, swing and drill-press table.
   The pool is a representative illustration of retrieval, not a retrieval ranking
   or a claim that these nine assets constitute the dataset.
2. **Edit**: four mixed variants of the same `crown_molding` cabinet. Two
   share the same walnut material; the other two use blue-gray paint and the
   yellow target finish. Proportions and handles vary together with materials.
   The tall walnut variant includes the original shelf/post mesh from
   `seed_0000`; the wide walnut cabinet retains an empty interior. Both the
   retrieved cabinet and all four edits are shown at 0.98 radians (about 56°),
   exposing the interior while remaining inside the original 102° door travel.
   The native T-bar dimensions are translated radially by 25 mm to match this
   cabinet. These are presentation edits, not new evaluated training samples.
3. **Train in simulation**: a close-up of the left Piper arm pushing the blue-gray
   cabinet open. Pose and door state come from simulation frame 900. The cabinet
   scale is 0.66, exactly as in `isaac_route/common/sim_asset.py`. A light spatial
   grid and an arc around the real door axis show the simulation context and motion.
4. **Deploy zero-shot**: a close-up of the right Piper arm pushing the yellow
   target cabinet closed, with a reversed motion arrow and a graphite hardware
   finish. It uses simulation frame 1800 as the pose for a deployment illustration;
   it is not a recovered real-world robot pose, photograph, or real trial.
   The actual real-world recordings remain immediately below the workflow.

The two close-ups illustrate two phases of the same open/close task, not different
training and deployment task definitions. Only the working arm is visible; its
native pose and distal geometry are preserved and the idle arm is hidden. The
deployment view also hides the base and two proximal links where they otherwise
intrude at the bottom-right edge. The close framing gives the object and gripper
most of the image area.

Editing is optional in the paper. The four-panel flow illustrates the edited
branch; it does not redefine all three experimental training conditions.

## Source assets and materials

- Cabinet: `/opt/isaacsim/sim_asset/round_cabinet/crown_molding/model.urdf`.
- Handle: `/opt/isaacsim/sim_asset/round_cabinet/t_bar/model.py` and `model.urdf`.
- Robot: `/opt/isaacsim/piper_official_isaac_asset_20260827/official_source/piper_with_gripper.urdf`;
  original Collada geometry is imported intact; the simulation panel retains the
  source robot materials and the deployment schematic uses a graphite finish.
- Robot pose: `/opt/isaacsim/end/real_sim_fixed_camera_20261014/round_cabinet/round_cabinet_fixed_camera.jsonl`.
- Dataset pool: existing native exports under `public/models/dataset/`, with their
  source provenance in `public/data/dataset.json`.
- Retrieved cabinet base colors: original URDF material palette. Adjacent appearance manifests
  contain incomplete texture references; these are not replaced with invented textures.
- Target cabinet material: the runtime USD appearance layer, diffuse `(0.23, 0.19, 0.045)`
  and roughness 0.85. This appears in one edit and the deployment panel. The training panel uses the
  same blue-gray finish as another edit.

The two walnut variants share one procedural wood shader definition; this is an
illustrative material edit, not a claimed source dataset texture. The shelf/post
visual is imported from the native `seed_0000/model.urdf`, without changing its
mesh. It attaches to the cabinet body; the other variants retain the original empty cavity.

Sources remain read-only. Lighting, camera placement, selection brackets, display
plinths, simulation grid and motion arrows are presentation elements. Lettering, borders and
arrows outside the panels are composed with Pillow, using a sans-serif font.

## Reproduce

Use Blender 4.2 LTS (its Collada importer is needed). Run the following for each of
`retrieve`, `edit`, `train`, `deploy`; independent panels can use different idle GPUs:

```bash
CUDA_VISIBLE_DEVICES=0 /tmp/blender-4.2.21-linux-x64/blender -b -t 8 \
  --python-exit-code 1 --python scripts/render_robotics_workflow.py -- retrieve
python scripts/compose_robotics_workflow.py
```

Final renders use Cycles OptiX, 128 samples and denoising, at 1280 × 1280 per panel.
Temporary PNGs, Blender scenes and logs live in `/tmp/rfw-workflow`. Composition
writes `public/media/robotics-flow.webp` (2854 × 742) and
`public/media/robotics-flow-mobile.webp` (1394 × 1612). The mobile return arrow
preserves reading order: retrieve, edit, train, deploy. Composition also updates
content hashes in the image/lightbox URLs so a new render does not reuse a cached
previous revision.

`render-audit.json` records sources, edits, devices and native URDF forward-kinematics
agreement with the recorded robot finger poses (maximum position error is recorded in the audit).
This verifies pose import, not physics validity of the illustrative edits.
