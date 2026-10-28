import './editing.css';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const $ = (s) => document.querySelector(s);
const base = import.meta.env.BASE_URL;
const url = (p) => base + p;
const KIND_LABELS = { component: 'Component', count: 'Part count', material: 'Material', size: 'Dimension' };

const LIVE_OBJECT = 'cabinet_paper_showcase';
const LIVE_BASE = { door_kind: 'flush_slab', door_count: 2, carcass_width_m: 1.0 };
const LIVE_GLUE = `
import sys, types, importlib.machinery, json
sys.path.insert(0, '/app')
_m = types.ModuleType('manifold3d')
_m.__spec__ = importlib.machinery.ModuleSpec('manifold3d', loader=None)
def _boom(*a, **k): raise RuntimeError('manifold3d stubbed out')
_m.__getattr__ = lambda name: _boom
sys.modules['manifold3d'] = _m
from pathlib import Path
from sdk import AssetContext, Material
from specific_editing.generators import get_generator
from specific_editing.export import export_visual_assets
from specific_editing.selectors import part_selectors, matches_surface
_reg = get_generator('cabinet')

def _set_material(model, target, rgba):
    patterns = part_selectors([target])
    mat = Material(name='live_edit', rgba=tuple(rgba))
    for part in model.parts:
        for i, visual in enumerate(part.visuals):
            if matches_surface(patterns, part_name=part.name, visual_name=str(visual.name or 'v%d' % i), visual=visual):
                visual.material = mat

def live_build(cfg_json):
    cfg = json.loads(cfg_json)
    cfgd = {k: v for k, v in cfg.items() if v is not None and not k.endswith('_mat')}
    model = _reg.build(_reg.make_config(cfgd, seed=None), assets=AssetContext('/tmp/live_assets'))
    if cfg.get('door_mat'): _set_material(model, 'door', cfg['door_mat'])
    if cfg.get('carcass_mat'): _set_material(model, 'carcass', cfg['carcass_mat'])
    export_visual_assets(model, Path('/tmp/live_out'))
    return Path('/tmp/live_out/scene.glb').read_bytes()
`;

const state = {
  data: null, object: null, kind: null, axis: null, variant: null,
  refView: null, newView: null, syncing: false,
  frames: new Map(), ready: false,
};
const live = { on: false, py: null, loading: null, cfg: null, seq: 0, blobUrl: null, debounce: 0 };
state.live = live;
const objectIsLive = () => state.object?.id === LIVE_OBJECT;

const zhMap = [
  [/更?宽|加宽|宽一点/, ['wider']],
  [/更?窄/, ['narrower']],
  [/更?(大|高)|放大/, ['bigger']],
  [/更?小|缩小/, ['smaller']],
  [/胡桃/, ['walnut']], [/橡木|橡树/, ['oak']], [/铝|拉丝/, ['aluminum', 'brushed', 'silver']],
  [/红/, ['red']], [/白/, ['white']], [/黑/, ['black']], [/蓝/, ['blue']],
  [/玻璃/, ['glass']], [/黄铜|金色/, ['brass', 'gold']],
  [/藤编/, ['cane']], [/门/, ['door']], [/面板|板/, ['panel']],
  [/座椅|座位/, ['seat']], [/座舱/, ['gondola', 'cabin', 'pod', 'capsule']],
  [/球杆|杆/, ['rod']], [/腿|支撑/, ['leg', 'trestle', 'support']],
  [/网/, ['mesh']], [/栅|条/, ['picket', 'slatted']],
];

function buildPromptIndex(object) {
  const entries = [];
  object.axes.forEach((axis, ai) => {
    axis.variants.forEach((v, vi) => {
      const words = `${v.button} ${v.label} ${axis.target} ${axis.kind}`.toLowerCase();
      const tokens = new Set(words.split(/[^a-z0-9.]+/).filter(Boolean));
      entries.push({ ai, vi, tokens, axis, v });
    });
  });
  return entries;
}

function matchPrompt(object, prompt) {
  const p = prompt.toLowerCase().trim();
  if (!p) return null;
  const entries = buildPromptIndex(object);
  const numbers = (p.match(/\d+(\.\d+)?/g) || []).map(Number);
  const synonyms = zhMap.flatMap(([re, words]) => (re.test(p) ? words : []));
  const words = new Set((p.match(/[a-z]+/g) || []).concat(synonyms));

  // Numbers select count/size variants directly.
  if (numbers.length) {
    for (const e of entries) {
      if (e.axis.kind === 'count' && numbers.includes(Number(e.v.button))) return e;
    }
    for (const e of entries) {
      if (e.axis.kind === 'size' && numbers.some((n) => Math.abs(n - Number(e.v.button)) < 1e-9)) return e;
    }
  }
  // Comparative words drive the size axis.
  if (/(wider|bigger|larger|taller|longer)/.test(p)) return extreme(entries, 'size', 1);
  if (/(narrower|smaller|shorter|slimmer)/.test(p)) return extreme(entries, 'size', -1);
  if (/(more|extra|additional)/.test(p)) return extreme(entries, 'count', 1);
  if (/(fewer|less)/.test(p)) return extreme(entries, 'count', -1);
  // Keyword overlap against variant labels.
  let best = null, bestScore = 0;
  for (const e of entries) {
    let score = 0;
    for (const w of words) if (e.tokens.has(w)) score += w.length;
    if (score > bestScore) { best = e; bestScore = score; }
  }
  return bestScore > 0 ? best : null;
}

function extreme(entries, kind, dir) {
  const group = entries.filter((e) => e.axis.kind === kind);
  if (!group.length) return null;
  const numeric = group.filter((e) => !Number.isNaN(Number(e.v.button)));
  if (!numeric.length) return null;
  numeric.sort((a, b) => Number(a.v.button) - Number(b.v.button));
  return dir > 0 ? numeric[numeric.length - 1] : numeric[0];
}

function variantLabel(v, axis) {
  return axis.kind === 'material' || axis.kind === 'component' ? v.label : `${axis.label}: ${v.button}`;
}

async function ensureViewers() {
  if (state.refView) return;
  const { AssetViewer } = await import('./viewer.js');
  state.refView = new AssetViewer($('#edit3d-ref'));
  state.newView = new AssetViewer($('#edit3d-new'));
  for (const [a, b] of [[state.refView, state.newView], [state.newView, state.refView]]) {
    a.controls.addEventListener('change', () => {
      if (state.syncing) return;
      state.syncing = true;
      b.camera.position.copy(a.camera.position);
      b.controls.target.copy(a.controls.target);
      b.controls.update();
      state.syncing = false;
    });
  }
}

async function groupFrame(object, axis) {
  const key = `${object.id}/${axis.group}`;
  if (state.frames.has(key)) return state.frames.get(key);
  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  const box = new THREE.Box3();
  const paths = [object.baseGlb, ...axis.variants.map((v) => v.glb)];
  const gltfs = await Promise.all(paths.map((p) => loader.loadAsync(url(p))));
  for (const g of gltfs) {
    g.scene.rotation.x = -Math.PI / 2; // editing-pipeline GLBs are Z-up
    g.scene.updateMatrixWorld(true);
    box.union(new THREE.Box3().setFromObject(g.scene));
    g.scene.traverse((o) => {
      o.geometry?.dispose();
      if (o.material) for (const m of [].concat(o.material)) { for (const val of Object.values(m)) if (val?.isTexture) val.dispose(); m.dispose(); }
    });
  }
  state.frames.set(key, box);
  return box;
}

function applyFrame(box) {
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const r = Math.max(size.x, size.y, size.z, 0.01);
  for (const v of [state.refView, state.newView]) {
    v.camera.position.set(center.x + r * 1.35, center.y + r * 0.8, center.z + r * 1.5);
    v.camera.near = r / 1000; v.camera.far = r * 100;
    v.camera.updateProjectionMatrix();
    v.controls.target.copy(center);
    v.controls.minDistance = r * 0.2; v.controls.maxDistance = r * 7;
    v.controls.update();
  }
}

function renderObjects() {
  $('#edit3d-objects').innerHTML = state.data.objects.map((o, i) =>
    `<button role="tab" aria-selected="${o === state.object}" data-i="${i}"><img src="${url(o.thumbnail)}" alt="${o.name}" loading="lazy"/><span>${o.name}</span></button>`
  ).join('');
  $('#edit3d-objects').querySelectorAll('button').forEach((b) =>
    b.addEventListener('click', () => selectObject(Number(b.dataset.i))));
}

function renderKinds() {
  const kinds = [...new Set(state.object.axes.map((a) => a.kind))];
  $('#edit3d-kinds').innerHTML = kinds.map((k, i) =>
    `<button role="tab" aria-selected="${k === state.kind}" data-k="${k}">${String(i + 1).padStart(2, '0')} <span>${KIND_LABELS[k]}</span></button>`
  ).join('');
  $('#edit3d-kinds').querySelectorAll('button').forEach((b) =>
    b.addEventListener('click', () => selectKind(b.dataset.k)));
}

function renderAxes() {
  const axes = state.object.axes.filter((a) => a.kind === state.kind);
  const wrap = $('#edit3d-axes');
  if (axes.length < 2) { wrap.innerHTML = ''; wrap.hidden = true; return; }
  wrap.hidden = false;
  wrap.innerHTML = axes.map((a) =>
    `<button aria-pressed="${a === state.axis}" data-g="${a.group}">${a.label}</button>`
  ).join('');
  wrap.querySelectorAll('button').forEach((b) =>
    b.addEventListener('click', () => selectAxis(axes.find((a) => a.group === b.dataset.g))));
}

function renderVariants() {
  $('#edit3d-variants').innerHTML = '<legend class="sr-only">Select an edited configuration</legend>' +
    state.axis.variants.map((v) => {
      const sw = v.swatch ? `<i class="swatch" style="background:rgba(${v.swatch.slice(0, 3).map((c) => Math.round(c * 255)).join(',')},${v.swatch[3]})"></i>` : '';
      const pressed = live.on && objectIsLive() ? variantMatchesLive(v, state.axis) : v === state.variant;
      return `<button aria-pressed="${pressed}" data-id="${v.id}">${sw}${v.button}</button>`;
    }).join('');
  $('#edit3d-variants').querySelectorAll('button').forEach((b) =>
    b.addEventListener('click', () => selectVariant(state.axis.variants.find((v) => v.id === b.dataset.id))));
  $('#edit3d-new-cap').textContent = live.on && objectIsLive() ? 'built live in your browser' : variantLabel(state.variant, state.axis);
  $('#edit3d-code').textContent = live.on && objectIsLive() ? liveReadout() : state.variant.readout;
}

async function loadPair() {
  if (live.on && objectIsLive()) return;
  const { object, axis, variant } = state;
  $('#edit3d-ref-cap').textContent = `${object.name} — reference configuration`;
  const box = await groupFrame(object, axis);
  await state.refView.load(url(object.baseGlb), { recenter: false, autoFrame: false, zUp: true });
  if (variant !== state.variant || axis !== state.axis) return; // stale
  await state.newView.load(url(variant.glb), { recenter: false, autoFrame: false, zUp: true });
  if (variant !== state.variant || axis !== state.axis) return;
  applyFrame(box);
}

function selectObject(i) {
  state.object = state.data.objects[i];
  if (live.on && !objectIsLive()) setLive(false);
  $('#edit3d-live').hidden = !objectIsLive();
  renderObjects();
  selectKind(state.object.axes[0].kind, true);
  renderChips();
}

function selectKind(kind) {
  state.kind = kind;
  renderKinds();
  selectAxis(state.object.axes.find((a) => a.kind === kind));
}

function selectAxis(axis) {
  state.axis = axis;
  renderAxes();
  if (live.on && objectIsLive()) {
    renderVariants();
    syncSlider();
    return;
  }
  const preferred = axis.variants[Math.min(1, axis.variants.length - 1)];
  selectVariant(preferred);
}

function selectVariant(v) {
  state.variant = v;
  if (live.on && objectIsLive()) {
    applyLiveVariant(state.axis, v);
    renderVariants();
    buildLive();
    return;
  }
  renderVariants();
  loadPair();
}

function renderChips() {
  const o = state.object;
  const chips = [];
  const noun = (t) => {
    let w = t.replace(/_/g, ' ').replace(/^num\s/, '').replace(/\s+count$/, '').trim();
    return /s$/.test(w) ? w : `${w}s`;
  };
  const count = o.axes.find((a) => a.kind === 'count');
  if (count) chips.push(`${count.variants[count.variants.length - 1].button} ${noun(count.target)}`);
  const mat = o.axes.filter((a) => a.kind === 'material').at(-1);
  if (mat) {
    const b = mat.variants[Math.min(1, mat.variants.length - 1)].button;
    const t = mat.target.replace(/_/g, ' ');
    chips.push(b.toLowerCase().includes(t.toLowerCase()) ? b : `${b} ${t}`);
  }
  const size = o.axes.find((a) => a.kind === 'size');
  if (size) chips.push(`make it ${/width/.test(size.target) ? 'wider' : /len/.test(size.target) ? 'longer' : 'bigger'}`);
  const comp = o.axes.find((a) => a.kind === 'component');
  if (comp) chips.push(`${comp.variants[comp.variants.length - 1].button}`);
  $('#edit3d-chips').innerHTML = chips.map((c) => `<button type="button">${c}</button>`).join('');
  $('#edit3d-chips').querySelectorAll('button').forEach((b) =>
    b.addEventListener('click', () => { $('#edit3d-prompt').value = b.textContent; applyPrompt(); }));
}

function applyPrompt() {
  const prompt = $('#edit3d-prompt').value;
  if (live.on && objectIsLive()) {
    const w = prompt.match(/\d+\.\d+/);
    if (w) {
      live.cfg.carcass_width_m = Math.min(1.5, Math.max(0.66, Number(w[0])));
      syncSlider();
      renderVariants();
      buildLive();
      $('#edit3d-prompt-note').textContent = `Matched: Cabinet width (m) → ${live.cfg.carcass_width_m}`;
      return;
    }
  }
  const hit = matchPrompt(state.object, prompt);
  const note = $('#edit3d-prompt-note');
  if (!hit) {
    note.textContent = 'No matching edit — try one of the examples below.';
    return;
  }
  note.textContent = `Matched: ${hit.axis.label} → ${hit.v.button}`;
  state.kind = hit.axis.kind;
  renderKinds();
  state.axis = hit.axis;
  renderAxes();
  selectVariant(hit.v);
}

const NOTE_PRECOMPUTED = 'All outputs are precomputed runs of the category generators; prompts are parsed locally and mapped to the matching configuration. Models are baked in a fixed pose — joint interaction lives in the asset explorer. Cameras share a fixed frame per edit axis, so size edits stay true to scale.';
const NOTE_LIVE = 'Live mode: the real cabinet generator runs in your browser (Pyodide WASM). Every build is computed on demand — any combination of the controls above. Materials are flat placeholder colors; the paper renders use the offline PBR pipeline.';

function variantMatchesLive(v, axis) {
  const c = live.cfg;
  if (!c) return false;
  if (axis.kind === 'component') return v.id.endsWith(`-${c.door_kind}`);
  if (axis.kind === 'count') return Number(v.button) === c.door_count;
  if (axis.kind === 'size') return Math.abs(Number(v.button) - c.carcass_width_m) < 1e-9;
  if (axis.kind === 'material') {
    const sel = c[`${axis.target}_mat`];
    return sel && v.swatch ? sel.every((x, i) => Math.abs(x - v.swatch[i]) < 1e-6) : false;
  }
  return false;
}

function applyLiveVariant(axis, v) {
  const c = live.cfg;
  if (axis.kind === 'component') c.door_kind = v.id.split('-').pop();
  else if (axis.kind === 'count') c.door_count = Number(v.button);
  else if (axis.kind === 'size') { c.carcass_width_m = Number(v.button); syncSlider(); }
  else if (axis.kind === 'material') c[`${axis.target}_mat`] = v.swatch || null;
}

function liveReadout() {
  const c = live.cfg, d = [];
  if (c.door_kind !== LIVE_BASE.door_kind) d.push(`door_kind: "${LIVE_BASE.door_kind}" → "${c.door_kind}"`);
  if (c.door_count !== LIVE_BASE.door_count) d.push(`door_count: ${LIVE_BASE.door_count} → ${c.door_count}`);
  if (Math.abs(c.carcass_width_m - LIVE_BASE.carcass_width_m) > 1e-9) d.push(`carcass_width_m: ${LIVE_BASE.carcass_width_m} → ${c.carcass_width_m}`);
  if (c.door_mat) d.push('door_material: default → custom');
  if (c.carcass_mat) d.push('carcass_material: default → custom');
  return d.join('; ') || 'base configuration (built live)';
}

function syncSlider(updateInput = true) {
  const row = $('#edit3d-slider');
  const show = live.on && objectIsLive() && state.kind === 'size';
  row.hidden = !show;
  if (!show) return;
  if (updateInput) $('#edit3d-width').value = live.cfg.carcass_width_m;
  $('#edit3d-slider-val').textContent = `${live.cfg.carcass_width_m.toFixed(2)} m`;
}

function setLive(on) {
  live.on = on;
  const btn = $('#edit3d-live');
  btn.setAttribute('aria-pressed', String(on));
  btn.textContent = on ? 'Live mode: on' : 'Live mode';
  $('#edit3d-live-status').textContent = '';
  $('#edit3d-note').textContent = on ? NOTE_LIVE : NOTE_PRECOMPUTED;
}

async function toggleLive() {
  if (live.on) {
    setLive(false);
    renderVariants();
    loadPair();
    return;
  }
  const btn = $('#edit3d-live'), status = $('#edit3d-live-status');
  btn.disabled = true;
  status.textContent = 'loading Python runtime (~17 MB, first time only)…';
  try {
    await ensureLive();
  } catch (err) {
    console.error('live mode failed', err);
    btn.disabled = false;
    status.textContent = 'live mode unavailable in this browser — precomputed variants unaffected';
    return;
  }
  btn.disabled = false;
  live.cfg = { ...live.manifest.baseConfig, door_mat: null, carcass_mat: null };
  setLive(true);
  renderVariants();
  syncSlider();
  buildLive();
}

async function ensureLive() {
  if (live.py) return live.py;
  if (!live.loading) {
    live.loading = (async () => {
      const manifest = await fetch(url('live/live.json')).then((r) => r.json());
      live.manifest = manifest;
      const vendorBase = new URL(`${manifest.vendorDir}/`, document.baseURI).href;
      const mod = await import(/* @vite-ignore */ new URL('pyodide.mjs', vendorBase).href);
      const py = await mod.loadPyodide({ indexURL: vendorBase });
      await py.loadPackage('numpy');
      const zipData = await fetch(url(manifest.zip)).then((r) => r.arrayBuffer());
      py.FS.mkdirTree('/app');
      py.unpackArchive(new Uint8Array(zipData), 'zip', { extractDir: '/app' });
      py.runPython(LIVE_GLUE);
      return py;
    })();
  }
  try {
    live.py = await live.loading;
  } catch (err) {
    live.loading = null;
    throw err;
  }
  return live.py;
}

async function buildLive() {
  if (!live.on || !objectIsLive() || !live.py || !live.cfg) return;
  const seq = ++live.seq;
  let u8;
  try {
    live.py.globals.set('__live_cfg', JSON.stringify(live.cfg));
    const proxy = live.py.runPython('live_build(__live_cfg)');
    const view = proxy.getBuffer();
    u8 = new Uint8Array(view.data.byteLength);
    u8.set(view.data);
    view.release();
    proxy.destroy();
  } catch (err) {
    console.error('live build failed', err);
    $('#edit3d-live-status').textContent = 'build failed for this configuration';
    return;
  }
  if (seq !== live.seq) return;
  if (live.blobUrl) URL.revokeObjectURL(live.blobUrl);
  live.blobUrl = URL.createObjectURL(new Blob([u8], { type: 'model/gltf-binary' }));
  const ok = await state.newView.load(live.blobUrl, { recenter: false, autoFrame: false, zUp: true });
  if (!ok || seq !== live.seq) return;
  const sizeAxis = state.object.axes.find((a) => a.kind === 'size');
  applyFrame(await groupFrame(state.object, sizeAxis));
  $('#edit3d-new-cap').textContent = 'built live in your browser';
  $('#edit3d-code').textContent = liveReadout();
}

async function boot() {
  const section = $('#editing');
  if (!section) return;
  state.data = await fetch(url('data/editing.json')).then((r) => r.json());
  renderObjects();
  new IntersectionObserver(async ([e], obs) => {
    if (!e.isIntersecting) return;
    obs.disconnect();
    await ensureViewers();
    state.ready = true;
    selectObject(0);
    window.rfwEditing = state;
    window.__editingReady = true;
  }, { rootMargin: '300px' }).observe(section);
  $('#edit3d-prompt-form').addEventListener('submit', (e) => { e.preventDefault(); applyPrompt(); });
  $('#edit3d-live').addEventListener('click', toggleLive);
  $('#edit3d-width').addEventListener('input', (e) => {
    live.cfg.carcass_width_m = Number(e.target.value);
    syncSlider(false);
    renderVariants();
    clearTimeout(live.debounce);
    live.debounce = setTimeout(buildLive, 80);
  });
}

boot();
