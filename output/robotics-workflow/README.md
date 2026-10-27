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
3. **Simulation training**: the taller cabinet is presented as a flat-lit CAD
   viewport, with component contours and cavity shading. The original left Piper
   pose and door angle come from simulation frame 900, with cabinet scale 0.66.
   Workbench display colors preserve the yellow cabinet / light robot identity;
   there is no floor grid or studio contact shadow. The motion arc still shows opening.
4. **Real-world deployment**: the yellow target is 28% shorter while retaining
   its radius and the original knob dimensions. The right Piper forearm uses the
   frame-1800 simulation pose, translated downward by the change in handle height
   (about 53 mm) so its contact remains aligned. A slightly higher camera, complete
   PBR shading and contact shadows provide a physical deployment schematic.
   Both robot panels use the same orthographic scale, preserving the visible size
   difference rather than enlarging the shorter cabinet to fill the frame.
   This is not a recovered real-world pose, photograph or real trial. Actual
   real-world recordings remain immediately below the workflow.

The two close-ups illustrate two phases of the same open/close task, not different
training and deployment task definitions. Only the working arm is visible; its
source joint angles and distal geometry are preserved and the idle arm is hidden.
The deployment forearm has the explicitly recorded presentation translation above. The
deployment view also hides the base and two proximal links where they otherwise
intrude at the bottom-right edge. The close framing gives the object and gripper
most of the image area.

Editing is optional in the paper. The four-panel flow illustrates the edited
branch; it does not redefine all three experimental training conditions.

## Source assets and materials

- Cabinet: `/opt/isaacsim/sim_asset/round_cabinet/crown_molding/model.urdf`.
- Handle: `/opt/isaacsim/sim_asset/round_cabinet/t_bar/model.py` and `model.urdf`.
- Robot: `/opt/isaacsim/piper_official_isaac_asset_20260827/official_source/piper_with_gripper.urdf`;
  original Collada geometry is imported intact; the simulation panel uses a flat light-gray viewport palette and the
  deployment schematic uses a graphite finish.
- Robot pose: `/opt/isaacsim/end/real_sim_fixed_camera_20261014/round_cabinet/round_cabinet_fixed_camera.jsonl`.
- Dataset pool: existing native exports under `public/models/dataset/`, with their
  source provenance in `public/data/dataset.json`.
- Retrieved cabinet base colors: original URDF material palette. Adjacent appearance manifests
  contain incomplete texture references; these are not replaced with invented textures.
- Target cabinet material: the runtime USD appearance layer, diffuse `(0.23, 0.19, 0.045)`
  and roughness 0.85. The same finish appears in one edit and both the training and deployment panels.

The two walnut variants share one procedural wood shader definition; this is an
illustrative material edit, not a claimed source dataset texture. The shelf/post
visual is imported from the native `seed_0000/model.urdf`, without changing its
mesh. It attaches to the cabinet body; the other variants retain the original empty cavity.

Sources remain read-only. Lighting, camera placement, selection brackets, display
plinths and motion arrows are presentation elements. Lettering, borders and
arrows outside the panels are composed with Pillow, using a sans-serif font.

## Reproduce

Use Blender 4.2 LTS (its Collada importer is needed). Run the following for each of
`retrieve`, `edit`, `train`, `deploy`; independent panels can use different idle GPUs:

```bash
CUDA_VISIBLE_DEVICES=0 /tmp/blender-4.2.21-linux-x64/blender -b -t 8 \
  --python-exit-code 1 --python scripts/render_robotics_workflow.py -- retrieve
python scripts/compose_robotics_workflow.py
```

Final panels are 1280 × 1280. Retrieval, edits and deployment use Cycles OptiX
with 128 samples and denoising; the simulation panel uses Workbench with 32-sample
antialiasing, flat illumination, material display colors and cavity contours.
Temporary PNGs, Blender scenes and logs live in `/tmp/rfw-workflow`. Composition
writes `public/media/robotics-flow.webp` (2854 × 742) and
`public/media/robotics-flow-mobile.webp` (1394 × 1612). The mobile return arrow
preserves reading order: retrieve, edit, train, deploy. Composition also updates
content hashes in the image/lightbox URLs so a new render does not reuse a cached
previous revision.

`render-audit.json` records sources, edits, devices and native URDF forward-kinematics
agreement with the recorded robot finger poses (maximum position error is recorded in the audit).
This verifies pose import, not physics validity of the illustrative edits.

The enlarged image viewer has no visible caption below the picture; accessible
image descriptions remain available as alt text.

The last two headings explicitly distinguish simulation training and real-world
deployment. Both cabinets retain the target yellow material identity. The simulation panel
uses a lighting-independent viewport display color, while the deployment schematic
uses the original PBR shader. Robot finishes remain light versus graphite.
