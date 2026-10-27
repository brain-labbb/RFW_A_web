# Robotics workflow: native asset renders

The website uses four Blender-rendered panels, short headings and connecting
arrows. There are no AI-generated objects or extracted video frames in this
version. Desktop and mobile WebP assets are about 90 KB each.

## Panel content

1. **Retrieve from 400K+**: eight multi-category dataset assets surround one
   highlighted round cabinet. Examples include a satellite, rover, paint roller,
   drawer cabinet, prosthetic limb, sewing machine, swing and drill-press table.
   The pool is a representative illustration of retrieval, not a retrieval ranking
   or a claim that these nine assets constitute the dataset.
2. **Edit**: four illustrative variants of that same `crown_molding` cabinet:
   height scaled by 1.28; radius scaled by 1.30; native T-bar handle; target material.
   The T-bar dimensions come from `t_bar/model.py` and its radial placement is
   translated by 25 mm to match the selected cabinet. The diagrams are controlled
   presentation edits; they are not new evaluated training samples or dataset records.
3. **Train in simulation**: the round cabinet and official dual-Piper model use
   frame 700 of the recorded simulation state. The cabinet scale is 0.66, exactly
   as in `isaac_route/common/sim_asset.py`. A quiet tabletop grid denotes simulation.
4. **Deploy zero-shot**: a matched Blender schematic with a plain workbench.
   This is not a real experiment photograph or a reconstructed real trial. The
   actual real-world recordings remain immediately below the workflow.

Editing is optional in the paper. The four-panel flow illustrates the edited
branch; it does not redefine all three experimental training conditions.

## Source assets and materials

- Cabinet: `/opt/isaacsim/sim_asset/round_cabinet/crown_molding/model.urdf`.
- Handle: `/opt/isaacsim/sim_asset/round_cabinet/t_bar/model.py` and `model.urdf`.
- Robot: `/opt/isaacsim/piper_official_isaac_asset_20260827/official_source/piper_with_gripper.urdf`;
  original Collada visuals and materials are imported intact.
- Robot pose: `/opt/isaacsim/end/real_sim_fixed_camera_20261014/round_cabinet/round_cabinet_fixed_camera.jsonl`.
- Dataset pool: existing native exports under `public/models/dataset/`, with their
  source provenance in `public/data/dataset.json`.
- Cabinet base colors: original URDF material palette. Adjacent appearance manifests
  contain incomplete texture references; these are not replaced with invented textures.
- Target cabinet material: the runtime USD appearance layer, diffuse `(0.23, 0.19, 0.045)`
  and roughness 0.85. The same material appears in the edit and robot panels.

Sources remain read-only. Lighting, camera placement, selection brackets, display
plinths and workbench geometry are presentation elements. Lettering, borders and
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
preserves reading order: retrieve, edit, train, deploy.

`render-audit.json` records sources, edits, devices and native URDF forward-kinematics
agreement with the recorded robot finger poses (maximum position error below 0.5 µm).
This verifies pose import, not physics validity of the illustrative edits.
