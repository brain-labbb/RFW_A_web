import './editing.css';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const $ = (s) => document.querySelector(s);
const base = import.meta.env.BASE_URL;
const url = (p) => base + p;
const KIND_LABELS = { component: 'Component', count: 'Part count', material: 'Material', size: 'Dimension' };

const state = {
  data: null, object: null, kind: null, axis: null, variant: null,
  refView: null, newView: null, syncing: false,
  frames: new Map(), ready: false,
};

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
  $('#edit3d-kinds').innerHTML = kinds.map((k) =>
    `<button role="tab" aria-selected="${k === state.kind}" data-k="${k}">${KIND_LABELS[k]}</button>`
  ).join('');
  $('#edit3d-kinds').querySelectorAll('button').forEach((b) =>
    b.addEventListener('click', () => selectKind(b.dataset.k)));
}

function renderValues() {
  const axes = state.object.axes.filter((a) => a.kind === state.kind);
  const grouped = axes.length > 1;
  $('#edit3d-values').innerHTML = axes.map((a) => {
    const buttons = a.variants.map((v) => {
      const sw = v.swatch ? `<i class="swatch" style="background:rgba(${v.swatch.slice(0, 3).map((c) => Math.round(c * 255)).join(',')},${v.swatch[3]})"></i>` : '';
      return `<button aria-pressed="${v === state.variant}" data-g="${a.group}" data-id="${v.id}">${sw}${v.button}</button>`;
    }).join('');
    return grouped ? `<span class="edit3d-group"><span class="edit3d-group-label">${a.label}</span><span class="edit3d-group-buttons">${buttons}</span></span>` : buttons;
  }).join('');
  $('#edit3d-values').querySelectorAll('button').forEach((b) =>
    b.addEventListener('click', () => {
      const axis = axes.find((a) => a.group === b.dataset.g);
      selectVariant(axis, axis.variants.find((v) => v.id === b.dataset.id));
    }));
  $('#edit3d-new-cap').textContent = variantLabel(state.variant, state.axis);
  $('#edit3d-code').textContent = state.variant.readout;
}

async function loadPair() {
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
  renderObjects();
  selectKind(state.object.axes[0].kind);
}

function selectKind(kind) {
  state.kind = kind;
  renderKinds();
  const axis = state.object.axes.find((a) => a.kind === kind);
  selectVariant(axis, axis.variants[Math.min(1, axis.variants.length - 1)]);
}

function selectVariant(axis, v) {
  state.axis = axis;
  state.variant = v;
  renderValues();
  loadPair();
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
}

boot();
