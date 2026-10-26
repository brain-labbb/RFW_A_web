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

Replace each `null` with its public HTTPS URL and rebuild. Both sets of resource buttons update automatically.

## Included content

- Four scene videos and the supplied 2:24 film, with MP4 and WebM playback versions.
- 24 representative dataset samples across 12 categories, with category filtering, four same-generator seed families, and an on-demand 3D inspector for materials, parts, and individual URDF joints.
- 84 searchable scene asset instances, with browser GLBs, original authored animations, thumbnails, joint metadata, and material properties.
- Four directed-editing comparisons using existing generator outputs.
- A generator-cost calculator using the paper's $10.62 authoring estimate and $1.237 per-asset baseline. Compute cost is excluded.
- Dataset scale, asset quality, and articulation-estimation tables from the supplied paper. Numerical sorting and in-domain/category-OOD selection are supported.
- Five pairs of simulation and real manipulation videos.
- Paper title, authors, affiliations, abstract, and figures from `RFW_A_arxiv`.

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
