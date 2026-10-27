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

All three buttons deliberately remain **SOON**, including Paper. No local paper PDF is published. When public URLs are available, edit `public/data/resources.json`:

```json
{"paper": null, "code": null, "dataset": null}
```

Replace each `null` with its public HTTPS URL and rebuild. The three hero resource buttons update automatically. The footer contains only the citation and website credit.

## Included content

- Four scene videos and the supplied 2:24 film, with MP4 and WebM playback versions.
- 24 representative dataset samples across 12 categories, with category filtering, four same-generator seed families, and an on-demand 3D inspector for materials, parts, and individual URDF joints.
- 84 searchable scene asset instances, with browser GLBs, original authored animations, thumbnails, joint metadata, and material properties.
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
- `demo.html` / `src/demo.js`: the full-screen Interactive demo opened from the project page.
- `src/data.js`: page comparison values and editing metadata.
- `public/data/catalog.json`: 84 native scene asset instances.
- `public/data/dataset.json` / `src/dataset.js`: representative PV_A_vlm samples and the dataset gallery/inspector.
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

### Representative dataset preparation

The showcase reads `/data/oss_bucket_0/yuanbo/PV_A_vlm/assets` without modifying it. `scripts/prepare_dataset.py` records 24 selected seeds, original URDF joint metadata, material classes, and source hashes. The four families share a source-recorded template hash within each category: ceiling fans, drawer cabinets, satellites, and Ferris wheels. The page's release totals come from the paper, not extrapolation from these examples.

`scripts/export_dataset.py` runs in the existing Blender installation and exports source geometry, joint hierarchies, and PBR bindings to GLB. Texture resolution is reduced for the browser; primitive UVs use the exporter mapping. This is a web representation, not the original release format. The inspector applies URDF kinematics, not physics simulation. `scripts/finish_dataset.py` compresses previews and verifies that every exported model preserves its movable joint identities with no missing source textures. Renders and audit reports stay in `/tmp/rfw-dataset/`.

The 24 GLBs total about 69 MB, fetched individually only when a sample is selected. Thumbnail images are lazy loaded. Sample links use `?sample=<sample-id>#dataset`. The full dataset is not bundled or made accessible by this page.

### Browser checks

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/rfw-web/browsers npm test
TEST_URL=http://127.0.0.1:4174/ PLAYWRIGHT_BROWSERS_PATH=/tmp/rfw-web/browsers npm run test:dataset
```

Run against the preview server with `TEST_URL=http://127.0.0.1:4174/` if desired. The test checks catalog/file coverage, physical-value ranges, pending release buttons, model animation, scene/search/edit controls, result tables, video playback, desktop/mobile layouts, and browser/network errors. The full-screen demo has a separate smoke check for scene filtering, native geometry loading, and material properties. Reports and screenshots go to `/tmp/rfw-web/`.

The dataset test opens all 24 models, checks joint controls and part coloring, and exercises category filters, seed families, sample links, lazy model loading, and mobile layouts. Its reports and screenshots go to `/tmp/rfw-dataset/`.

Design references the section organization of [Artisan](https://physicalvision.github.io/artisan/) and dataset presentation of [Articraft](https://articraft3d.github.io/). Page implementation, assets, authors, and numerical results are specific to RFW-A.

## Scene walkthroughs

`Explore the scenes` now pairs a scene image with selectable object regions and an adjacent camera clip and property panel. Four scene maps expose three featured objects each; all 84 native instances remain available in the interactive demo. Object links open the selected asset directly. Close-ups are rendered from the native scene animation with new cameras, not live physics simulations.

The 12 five-second clips are rendered at 960 × 540, 24 fps with Cycles/OptiX. `scripts/scene_shots.json` records their camera endpoints and native frame ranges. `scripts/render_scene_batch.py final` schedules independent jobs across GPUs 0–7. Render output stays in `/tmp/rfw-scenes/`; `scripts/render_scene_maps.py -- <scene>` creates map images and projects the audited visual-mesh membership into clickable regions. `scripts/finish_scene_media.py` publishes compressed MP4/WebM clips, WebP images, and `public/data/scenes.json`.

For the space scene, `scripts/extend_space_stage.py` joins additional terrain to the existing boundary and replaces the finite star backdrop with a camera-visible panoramic dome using the native procedural material. Earth, asset geometry, rigs, and lighting are retained. These changes exist only in the render copy; the four original scene files are never overwritten. The space map uses native frame 240 to show the assembled scene.

Run `TEST_URL=http://127.0.0.1:4175/ PLAYWRIGHT_BROWSERS_PATH=/tmp/rfw-web/browsers npm run test:scenes` to verify all 12 clip selections, playback, materials and joints, map/video switching, mobile layouts, and direct 3D links.

## Video masthead

The first screen uses a full-width, muted scene video behind the paper title, all 22 authors, affiliations, and resource links. Its layout follows the supplied Artisan screenshot: a white navigation bar, white overlaid metadata, translucent buttons, and scene/playback controls along the bottom. The four scene buttons change the background. “Watch scene” hides the paper overlay; Escape or the Paper navigation restores it. “Explore this scene” selects the corresponding scene explorer.

“Watch full video” opens the supplied `2610261545030522.mp4` (2:24, including audio) using the existing film player; the published MP4 matches the supplied file byte-for-byte. Other videos pause while the film is open. Background playback pauses offscreen and respects reduced-motion and data-saving preferences. Benchmark remains a results section, without a navigation or hero button. Paper, Code, and Dataset links remain pending.

`npm run test:hero` checks scene switching/playback, overlay controls, the full film, pending links, mobile layout, and reduced-motion behavior. Set `TEST_URL` and `PLAYWRIGHT_BROWSERS_PATH` as in the other browser checks.

## Robotic manipulation gallery

`src/robotics.js` and `public/data/robotics.json` drive the six-video task gallery. `scripts/prepare_robotics.py` imports all 30 recordings from `/opt/isaacsim/end/real_sim_final_20261014`, verifies the source manifest SHA-256 hashes before encoding, and checks source integrity afterward. Full timelines and supplied frame dimensions are retained; no task motion is trimmed. MP4 and WebM copies are silent and encoded at 4× for simulation, 2× for real-world recordings, except the short folding-chair recording at 1×. The interface omits speed labels; encoding factors remain in the media metadata.

The paper representative simulation is shown first, followed by four other supplied simulation assets and the real-world target. The source manifest does not identify each clip with a specific retrieval/edit training configuration, so recordings are labelled as simulation examples; the three experimental configurations are reported separately using the Robotic Manipulation section of the paper. All use 500 simulation demonstrations per task, the same policy architecture and budget, and 10 real-world evaluation trials per task. The mean success rates are 62%, 72%, and 80%; detailed per-task results are expandable.

Simulation and real-world recordings appear in separate labelled groups, side by side on desktop and stacked on mobile. The five simulation variants share a compact grid; the real-world video is larger. Only the selected task's visible recordings load and play automatically in a muted loop. Offscreen/background playback pauses, and reduced-motion/data-saving preferences disable automatic playback. Enlarging a video pauses the gallery and supports Escape and native playback controls. The old pair-view media remain in the repository but are no longer loaded by the page.

Validation: `PLAYWRIGHT_BROWSERS_PATH=/tmp/rfw-web/browsers TEST_URL=http://localhost:4178/ npm run test:robotics`. Encoding audit and browser screenshots are written to `/tmp/rfw-robotics/`.

The robotics subtitle is an illustrated arrow workflow generated with `gpt-image-2` through the imagegen CLI using locally configured credentials. `output/imagegen/robotics-flow.prompt.txt` preserves the prompt, `robotics-flow-v1.png` preserves the original output, and `robotics-flow-plan.md` records preparation. The served WebP versions use a horizontal desktop layout and a two-row mobile layout. Labels explicitly preserve optional editing and simulation-only training.
