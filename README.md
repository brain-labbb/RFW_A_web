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
- `src/data.js`: page comparison values and editing metadata.
- `public/data/catalog.json`: 84 native scene asset instances.
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

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/rfw-web/browsers npm test
```

Run against the preview server with `TEST_URL=http://127.0.0.1:4174/` if desired. The test checks catalog/file coverage, physical-value ranges, pending release buttons, model animation, scene/search/edit controls, result tables, video playback, desktop/mobile layouts, and browser/network errors. Reports and screenshots go to `/tmp/rfw-web/`.

Design references the section organization of [Artisan](https://physicalvision.github.io/artisan/). Page implementation, visual design, assets, authors, and numerical results are specific to RFW-A.
