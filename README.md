# RFW-A project website

A standalone static research website for **RFW-A: Agentic Procedural Generation of 400K Articulated Assets over 500 Categories**.

## Preview and build

Requires Node.js 22+.

```bash
npm ci
npm run dev       # http://localhost:4173
npm run build    # deployable static files in dist/
npm run preview -- --port 4174
```

The build supports a subdirectory such as GitHub Pages. Deploy the contents of `dist/` to any static host. The project has no application server, database, or browser-side API credentials. All fonts, media, model files, and page data are local.

## Release links

The Paper button links to the public arXiv release; Code and Dataset buttons deliberately remain **SOON**. No local paper PDF is published. When public URLs are available, edit `public/data/resources.json`:

```json
{"paper": null, "code": null, "dataset": null}
```

Replace each `null` with its public HTTPS URL and rebuild. The three hero resource buttons update automatically. The footer contains only the citation and website credit.

## Included content

- Four scene videos and the supplied 2:24 film, with MP4 and WebM playback versions.
- One unified asset explorer: 30 image-grounded category families, six source seeds each (180 assets), input images, 2D preview cards, selectable parts, source physics, and on-demand MuJoCo simulation. All samples are reselected directly from `PV_A_vlm`. The tilt-truck family combines two source generator variants (2+4 seeds).
- Scene walkthroughs retain their images, videos, object selection, and physical-property panels. The old standalone scene-asset 3D viewer and its two scene links are retired.
- Four directed-editing comparisons using existing generator outputs.
- A generator-cost calculator using the paper's $10.62 authoring estimate and $1.237 per-asset baseline. Compute cost is excluded.
- Dataset scale, asset quality, and articulation-estimation tables from the supplied paper. Numerical sorting and in-domain/category-OOD selection are supported.
- All 30 robotics recordings: five simulation assets and one real-world recording per task, across five tasks. Shared playback, task thumbnails, enlarged video viewing, and paper-aligned results.
- Paper title, authors, affiliations, abstract, and results from `RFW_A_arxiv`.
- Method figure replaced on 2026-10-27 with the supplied `mmexport1793000691972.jpg`, losslessly encoded as WebP. It matches the supplied PPT diagram; the image avoids font substitutions in the local PowerPoint export. The original image and PPT remain untouched.

The 84 instances are a scene showcase, not the full 402,410-asset release. The scenes contain repeated geometry. Animation playback follows the native scene; this is not a live physics simulation. Original `.blend` files and source datasets remain untouched. The website does not distribute the paper PDF, baseline datasets, source code archive, or full dataset release.

## Main files

- `index.html`: page content and section structure.
- `src/style.css`: responsive typography, colors, layout; local font declarations.
- `src/main.js`: scene switching, explorer, editors, tables, dialogs, and videos.
- `src/viewer.js`: lazily loaded Three.js viewer and animation playback.
- `demo.html` / `src/demo.js`: compatibility redirect to the unified explorer; old scene assets are not loaded.
- `src/data.js`: page comparison values and editing metadata.
- `public/data/catalog.json`: 84 native scene asset instances.
- `public/data/explorer.json` / `src/explorer.js` / `src/explorer.css`: unified input-image, generator-family, and seed explorer.
- `src/simulation.js`: lazily loaded, pinned `@mujoco/mujoco` 3.17.0 WebAssembly runtime.
- `public/data/explorer/`: source part details and standalone simulation MJCF; `public/models/explorer/` and `public/media/explorer/`: models, seed previews, and input images.
- `public/data/physics/`: six physical-property fields per material group.
- `public/data/resources.json`: release URLs.

## Asset preparation

The preparatory scripts reference this machine's supplied handoff directory. They are not needed to serve or build the site.

- `scripts/prepare_media.py` imports supplied media, creates web images, and extracts paper metadata. Do not rerun after filling release links without preserving `resources.json`.
- `scripts/export_models.py` runs in existing Blender 5.2.2 and exports native geometry plus sampled authored motion. The source handoff was authored in 5.1.1; 5.2.2 was available and used to preserve forward compatibility.
- `scripts/web_video.py` adds WebM compatibility versions through transcoding only, with no new scene rendering.
- `scripts/inspect_materials.py` extracts current Blender material names, PBR values, and mesh associations.
- `scripts/annotate_physics.py` is an **offline** Qwen annotation job. It accepts a path to an external credential JSON. Never put a key in this repository. The job uses `qwen3.8-max`, checks output coverage and numerical ranges, and resumes from cached responses. Private audit data is kept in ignored `offline/physics-audit/` and excluded from the public build.
- `scripts/thumbnails.mjs` captures the actual browser models and writes WebP previews. Requires Playwright Chromium and Python/Pillow.

Existing source physics records were examined first; 57/84 assets have source-seed physics files. Current scene material assignments include refinements, so unresolved current-material mappings were annotated using Qwen. API results, assumptions, usage, and provenance are preserved only in the offline audit. The web panel presents a unified material-and-property interface. These annotations are not direct laboratory measurements or simulator validation results. Friction/restitution estimates use the annotation job's dry self-contact reference conditions.

## Validation

### Unified asset explorer

The gallery uses **30 categories × 6 seeds = 180 assets** from `/data/oss_bucket_0/yuanbo/PV_A_vlm/assets`. Input images come from `/home/lyuyuanbo.lyb/PVA/articraft_data/picture`. Source maps explicitly associate these images with the generator's upstream examples, citing the picture library under its historical `picture/`, `pictureX/` or `pictureY/` roots; four record-derived families (Astronaut helmets, Return capsules, Helicopters, Universal joints) instead pair the matching picture subclass folder with the modular spec as the recorded lineage. Each selected seed has the exact SHA-256 of the local category template. Multiple source images are exposed with small image buttons. `Input image` refers to a generator reference, not to a claim that each seed independently reconstructs that image.

Only images and the compact manifest load initially. Clicking a seed loads one GLB and its source property record. `Simulate` loads the engine and that seed's MJCF. All URDF links have buttons below the viewer, including fixed parts. Clicking a mesh selects its link; the surface selector exposes its material annotations. Joint sliders honor mimic dependencies. The engine supports run/pause/reset, gravity, and brief positive/negative joint-force pulses. Selection and shared URLs remain within this same exhibit.

Preparation uses the existing Blender 5.2.2 and Genesis Python environment, with all caches, source copies, render output, and reports under `/tmp/rfw-explorer/`:

```bash
/tmp/venvs/genesis/bin/python scripts/prepare_explorer.py
python scripts/render_explorer_batch.py
/tmp/venvs/genesis/bin/python scripts/finish_explorer.py
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 /tmp/venvs/genesis/bin/python scripts/export_explorer_physics.py
OPENBLAS_NUM_THREADS=1 /tmp/venvs/genesis/bin/python scripts/map_explorer_properties.py
/tmp/venvs/genesis/bin/python scripts/map_explorer_properties.py --apply
OPENBLAS_NUM_THREADS=1 /tmp/venvs/genesis/bin/python scripts/prepare_explorer_interaction.py
```

The mapping and interaction preparation steps run after physics export to preserve all records. The source datasets and templates are read-only. `scripts/explorer_exclusions.json` prevents withdrawn categories and samples from returning during preparation. The entire `Curtain_blind` category is withdrawn: flexible cords and shade fabric are outside the current rigid-body demo; all source data is preserved. The scripts skip candidates with missing physics records or mismatched generator versions. Seed selection favors different link/joint/visual structures, then material classes. GLBs preserve joint identities and source transforms; source textures are downsampled for the browser. Previews use a consistent camera direction and individual framing.

Source physical records sometimes group repeated surfaces or use descriptive names. Surface annotations are joined by unambiguous normalized names or verified scaled centroid and solid volume. Grouped annotations share material properties; their masses are never added repeatedly. Unmatched surface properties remain unavailable. Source link mass, center of mass, inertial tensor, joint limits, and dynamics retain their own provenance. Appearance materials and physical annotations are labeled separately when inspecting a surface.

Simulation is a **fixed-base rigid-body interaction demo**, not a reproduction of the paper's validation protocol. Concave source collision meshes use CoACD decomposition before MuJoCo compilation so openings are not replaced by one filled convex hull. Source inertial tensors that fail positivity or the triangle inequality receive recorded simulator-only projections; the inspector still displays the original source values. Missing source inertials use MuJoCo's geometry-derived defaults. Source `mu1` becomes sliding friction; torsional/rolling friction use declared defaults. The source restitution, Young's modulus, and Poisson ratio are displayed annotations, not soft-body parameters or an exact restitution conversion. Damped interaction is enabled by default: virtual joint damping is at least rated effort / rated speed, with a reflected armature of 2% child subtree mass (slide) or 2% mass × collision radius² (hinge). The checkbox restores source joint damping and armature when disabled. Missing rated effort uses subtree gravity force/torque; missing rated speed uses 0.1 m/s or 2 rad/s. These controls do not overwrite displayed source properties. A speed guard pauses at 10× rated/fallback speed and restores the previous pose; some source collision configurations still require a reset or joint adjustment. Directly connected rigid groups, including the fixed base, are excluded from self-contact; nonadjacent contact remains enabled. These adaptations are documented in the per-asset simulation records.

Run `npm run test:physics` for ten-second default-pose rollouts of all published models in the same MuJoCo WASM engine as the browser. These checks do not imply stability for arbitrary poses or forces. Run `npm run test:dataset` for all 30 families, part controls, joint motion, live MuJoCo, sample URLs, rapid switching, lazy loading, and 390/320px layouts. `npm test`, `npm run test:hero`, `npm run test:scenes`, and `npm run test:robotics` cover the other page features. Browser screenshots and the explorer report are written to `/tmp/rfw-explorer/`.

The hero retains **Explore this scene**, which selects and opens the current scene. The two additional hero actions (Explore scenes and Interactive demo) are removed. The top navigation has one Explore assets link for the unified exhibit.

## Scene walkthroughs

`Explore the scenes` now pairs a scene image with selectable object regions and an adjacent camera clip and property panel. Four scene maps expose 56 selectable objects (16 indoor, 16 outdoor, 9 space, 15 laboratory); the scene walkthrough remains independent of the dataset explorer. The obsolete scene-to-3D links are removed; scene selection and property panels remain available. Close-ups are rendered from the native scene animation with new cameras, not live physics simulations.

The 56 five-second clips are rendered at 960 × 540, 24 fps with Cycles/OptiX. `scripts/scene_shots.json` records their camera endpoints and native frame ranges. `scripts/render_scene_batch.py final` schedules independent jobs across GPUs 0–7. Render output stays in `/tmp/rfw-scenes/`; `scripts/render_scene_maps.py -- <scene>` creates map images and projects the audited visual-mesh membership into clickable regions. `scripts/finish_scene_media.py` publishes compressed MP4/WebM clips, WebP images, and `public/data/scenes.json`.

For the space scene, `scripts/extend_space_stage.py` joins additional terrain to the existing boundary and replaces the finite star backdrop with a camera-visible panoramic dome using the native procedural material. Earth, asset geometry, rigs, and lighting are retained. These changes exist only in the render copy; the four original scene files are never overwritten. The space map uses native frame 240 to show the assembled scene.

Run `TEST_URL=http://127.0.0.1:4175/ PLAYWRIGHT_BROWSERS_PATH=/tmp/rfw-web/browsers npm run test:scenes` to verify all 56 clip selections, playback, mass/materials, joint limits, dynamics and inertia, map/video switching, mobile layouts, and optional 3D links.

Part-level details follow the inspector structure on [Artisan](https://physicalvision.github.io/artisan/): total mass per instance, mass/materials, joint limits, joint dynamics, and inertia. `public/data/scene-physics/*.json` records per-field provenance. Matched source parameters are retained; ambiguous source seeds are not silently selected. Native groups belonging to the same source link are merged to avoid counting its mass twice. Missing masses, centers of mass, mass-distribution variances and dynamics are annotated with **qwen3.8-max**, `reasoning_effort: medium`. Missing inertia uses Qwen-estimated center-of-mass fractions and mass-distribution variances within native part bounds, converted to a physically consistent diagonal approximation; its COM and axes are explicitly labeled as scene-space estimates. Source inertia retains source link/inertial coordinates and RPY. These are model parameters, not measured physical validation.

To rebuild annotations, run `prepare_scene_expansion.py` with Blender once per scene (`-- indoor`, etc.), then `python scripts/annotate_scene_properties.py /path/to/api.txt`. The credential file is parsed without executing it; it is never copied to public assets. Cached responses, request fingerprints, usage, and estimate rationale stay in ignored `offline/scene-physics-audit/`. Run `python scripts/validate_scene_properties.py` to check full coverage, mass totals, duplicate source links, parameter ranges, and inertia tensors. Generated frames and validation screenshots stay in `/tmp/rfw-scenes/`.

## Video masthead

The first screen uses a full-width, muted scene video behind the paper title, all 22 authors, affiliations, and resource links. Its layout follows the supplied Artisan screenshot: a white navigation bar, white overlaid metadata, translucent buttons, and scene/playback controls along the bottom. The four scene buttons change the background. “Watch scene” hides the paper overlay; Escape or the Paper navigation restores it. “Explore this scene” selects the corresponding scene explorer.

“Watch full video” opens the supplied `2610261545030522.mp4` (2:24, including audio) using the existing film player; the published MP4 matches the supplied file byte-for-byte. Other videos pause while the film is open. Background playback pauses offscreen and respects reduced-motion and data-saving preferences. Benchmark remains a results section, without a navigation or hero button. The Paper link points to the arXiv release; Code and Dataset links remain pending.

`npm run test:hero` checks scene switching/playback, overlay controls, the full film, pending links, mobile layout, and reduced-motion behavior. Set `TEST_URL` and `PLAYWRIGHT_BROWSERS_PATH` as in the other browser checks.

## Robotic manipulation gallery

`src/robotics.js` and `public/data/robotics.json` drive the six-video task gallery. `scripts/prepare_robotics.py` imports all 30 recordings from `/opt/isaacsim/end/real_sim_final_20261014`, verifies the source manifest SHA-256 hashes before encoding, and checks source integrity afterward. Full timelines and supplied frame dimensions are retained; no task motion is trimmed. MP4 and WebM copies are silent and encoded at 4× for simulation, 2× for real-world recordings, except the short folding-chair recording at 1×. The interface omits speed labels; encoding factors remain in the media metadata.

The paper representative simulation is shown first, followed by four other supplied simulation assets and the real-world target. The source manifest does not identify each clip with a specific retrieval/edit training configuration, so recordings are labelled as simulation examples; the three experimental configurations are reported separately using the Robotic Manipulation section of the paper. All use 500 simulation demonstrations per task, the same policy architecture and budget, and 10 real-world evaluation trials per task. The mean success rates are 62%, 72%, and 80%; detailed per-task results are expandable.

Simulation and real-world recordings appear in separate labelled groups, side by side on desktop and stacked on mobile. The five simulation variants share a compact grid; the real-world video is larger. Only the selected task's visible recordings load and play automatically in a muted loop. Offscreen/background playback pauses, and reduced-motion/data-saving preferences disable automatic playback. Enlarging a video pauses the gallery and supports Escape and native playback controls. The old pair-view media remain in the repository but are no longer loaded by the page.

Validation: `PLAYWRIGHT_BROWSERS_PATH=/tmp/rfw-web/browsers TEST_URL=http://localhost:4178/ npm run test:robotics`. Encoding audit and browser screenshots are written to `/tmp/rfw-robotics/`.

The robotics subtitle is an illustrated arrow workflow generated with `gpt-image-2` through the imagegen CLI using locally configured credentials. `output/imagegen/robotics-flow.prompt.txt` preserves the prompt, `robotics-flow-v1.png` preserves the original output, and `robotics-flow-plan.md` records preparation. The served WebP versions use a horizontal desktop layout and a two-row mobile layout. Labels explicitly preserve optional editing and simulation-only training.
