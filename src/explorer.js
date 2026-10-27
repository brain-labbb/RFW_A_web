import './explorer.css';

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const url = path => import.meta.env.BASE_URL + path;
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty = value => String(value || '').replaceAll('_', ' ');
const number = value => Number.isFinite(value) ? Number(value.toPrecision(4)).toLocaleString('en-US', {maximumSignificantDigits:4}) : '—';
const unit = (value, suffix) => Number.isFinite(value) ? `${number(value)} ${suffix}` : '—';
const seedName = asset => `Seed ${String(asset.seed).padStart(4, '0')}`;
const fields = values => `<div class="gx-property-grid">${values.map(([name,value]) => `<div><small>${escape(name)}</small>${escape(value)}</div>`).join('')}</div>`;
let manifest, byId, family, selected, details, viewer, viewerPromise, rig = [], part = null;
let version = 0, expanded = false, partColors = false, simulation = null, simVersion = 0, loading = false;
let pointerStart;

function renderCategories() {
  const term = $('#gx-search').value.trim().toLowerCase(), domain = $('#gx-domain').value;
  const matches = manifest.families.filter(f => (domain === 'all' || f.domain === domain) && `${f.name} ${f.domain}`.toLowerCase().includes(term));
  const visible = expanded || term || domain !== 'all' ? matches : matches.slice(0, 16);
  $('#gx-count').textContent = `${manifest.families.length} featured categories · ${manifest.assets.length} generated samples`;
  $('#gx-categories').innerHTML = visible.length ? visible.map(f => `<button class="gx-category" data-category="${escape(f.id)}" aria-pressed="${f.id === family?.id}"><img src="${url(f.inputs[0].image)}" width="160" height="104" loading="lazy" alt=""/><span>${escape(f.name)}</span></button>`).join('') : '<p class="gx-empty">No matching categories. Try another name or filter.</p>';
  $('#gx-more').hidden = matches.length <= 16 || Boolean(term) || domain !== 'all';
  $('#gx-more').textContent = expanded ? 'Show fewer categories ↑' : `Show all ${matches.length} categories ↓`;
  $$('[data-category]').forEach(button => button.addEventListener('click', () => selectFamily(button.dataset.category)));
}

function showInput(index) {
  const input = family.inputs[index];
  $('#gx-input-image').src = url(input.image);
  $('#gx-input-image').alt = `${family.name}: source input image ${index + 1}`;
  $$('[data-input]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.input) === index)));
}

function renderSeeds() {
  $('#gx-seeds').innerHTML = family.samples.map(id => {
    const a = byId.get(id);
    return `<button class="gx-seed" data-seed="${escape(id)}" aria-pressed="${selected?.id === id}" aria-label="Explore ${escape(a.name)}, ${seedName(a)}"><img src="${url(a.image)}" width="640" height="480" alt="${escape(a.name)}, ${seedName(a)}" loading="lazy"/><span class="gx-seed-label">${seedName(a)}<small>${a.links} parts · ${a.joints.length} joints</small></span></button>`;
  }).join('');
  $$('[data-seed]').forEach(button => button.addEventListener('click', () => openAsset(button.dataset.seed, true)));
}

function stopSimulation() {
  ++simVersion;
  simulation?.dispose(); simulation = null;
  $('#gx-simulation').hidden = true;
  $('#gx-simulate').setAttribute('aria-pressed', 'false');
  $('#gx-simulate').textContent = 'Simulate';
}

function selectFamily(id) {
  if (family?.id === id) return;
  ++version; stopSimulation(); loading = false;
  family = manifest.families.find(f => f.id === id); selected = null; details = null; part = null;
  $('#gx-workbench').hidden = true; $('#gx-family').hidden = false;
  $('#gx-family-title').textContent = family.name;
  $('#gx-domain-label').textContent = family.domain.toUpperCase();
  $('#gx-family-count').textContent = `${family.samples.length} seeds from one shared generator`;
  $('#gx-input-choices').innerHTML = family.inputs.length > 1 ? family.inputs.map((input, i) => `<button data-input="${i}" aria-label="Input image ${i+1}" aria-pressed="${i===0}"><img src="${url(input.image)}" alt="" loading="lazy"/></button>`).join('') : '';
  $$('[data-input]').forEach(button => button.addEventListener('click', () => showInput(Number(button.dataset.input))));
  showInput(0); renderCategories(); renderSeeds();
}

async function getViewer() {
  if (!viewerPromise) viewerPromise = import('./viewer.js').then(({AssetViewer}) => {
    viewer = new AssetViewer($('#gx-viewer'));
    viewer.beforeRender = delta => {
      if (!simulation || loading) return;
      try {
        simulation.step(delta);
        simulation.positions().forEach((value, i) => setRigJoint(rig[i], value));
        viewer.model.updateMatrixWorld(true); jointUI();
        $('#gx-time').textContent = `${simulation.time.toFixed(2)} s`;
        $('#gx-play').textContent = simulation.running ? 'Ⅱ Pause' : '▶ Run';
      } catch (error) { status(error.message); }
    };
    const canvas = viewer.renderer.domElement;
    canvas.addEventListener('pointerdown', event => { pointerStart = [event.clientX, event.clientY]; });
    canvas.addEventListener('pointerup', event => {
      if (loading || !details || !pointerStart || Math.hypot(event.clientX-pointerStart[0], event.clientY-pointerStart[1]) > 5) return;
      const rect = canvas.getBoundingClientRect(), T = viewer.THREE;
      const ray = new T.Raycaster();
      ray.setFromCamera(new T.Vector2((event.clientX-rect.left)/rect.width*2-1, -(event.clientY-rect.top)/rect.height*2+1), viewer.camera);
      const hit = ray.intersectObject(viewer.model, true).find(x => x.object.userData.rfw_part);
      selectPart(hit?.object.userData.rfw_part || null);
    });
    return viewer;
  }).catch(error => { viewerPromise = null; throw error; });
  return viewerPromise;
}

function status(text) { $('#gx-status').textContent = text; $('#gx-status').hidden = !text; }
function setRigJoint(joint, value) {
  if (!joint) return;
  joint.value = value;
  joint.object.position.copy(joint.basePosition); joint.object.quaternion.copy(joint.baseRotation);
  if (joint.type === 'prismatic') joint.object.position.add(joint.axis.clone().applyQuaternion(joint.baseRotation).multiplyScalar(value));
  else joint.object.quaternion.multiply(new viewer.THREE.Quaternion().setFromAxisAngle(joint.axis, value));
}

function configureRig() {
  const nodes = new Map();
  viewer.model.traverse(object => { if (object.userData.rfw_joint) nodes.set(object.userData.rfw_joint, object); });
  rig = selected.joints.map(joint => {
    const object = nodes.get(joint.name);
    if (!object) throw Error(`Model joint missing: ${joint.name}`);
    const [x,y,z] = joint.axis;
    const continuous = joint.type === 'continuous';
    return {...joint, object, axis:new viewer.THREE.Vector3(x,z,-y).normalize(),
      lower:continuous ? -Math.PI : joint.lower ?? 0, upper:continuous ? Math.PI : joint.upper ?? 0,
      basePosition:object.position.clone(), baseRotation:object.quaternion.clone(), value:0};
  });
  $('#gx-joint').innerHTML = rig.map((j,i) => `<option value="${i}">${escape(pretty(j.name))}${j.mimic ? ' · linked' : ''}</option>`).join('');
  if (rig.length) $('#gx-joint').value = '0';
  $('#gx-joint').disabled = !rig.length; jointUI();
}

function jointUI() {
  const joint = rig[Number($('#gx-joint').value)];
  const enabled = !loading && joint && joint.upper > joint.lower && !joint.mimic;
  $('#gx-position').disabled = !enabled || Boolean(simulation?.running);
  $('#gx-force-minus').disabled = $('#gx-force-plus').disabled = !enabled;
  if (!joint) { $('#gx-position-output').textContent = '—'; $('#gx-joint-description').textContent = 'No movable joint.'; return; }
  $('#gx-position').value = String(Math.round((joint.value-joint.lower)/(joint.upper-joint.lower || 1)*1000));
  $('#gx-position-output').textContent = unit(joint.value, joint.type === 'prismatic' ? 'm' : 'rad');
  $('#gx-joint-description').textContent = `${joint.type} · ${number(joint.lower)} to ${number(joint.upper)}${joint.mimic ? ` · follows ${pretty(joint.mimic.joint)}` : ''}`;
  const pulse = (details?.simulation?.interaction?.joints.find(j=>j.name===joint.name)?.effort || (joint.effort > 0 ? joint.effort : 1)) * .5;
  for (const id of ['#gx-force-minus','#gx-force-plus']) $(id).title=`Apply ${number(pulse)} ${joint.type==='prismatic'?'N':'N·m'} for 0.15 seconds`;
}

function changePosition(fraction) {
  const joint = rig[Number($('#gx-joint').value)];
  if (!joint || joint.mimic) return;
  setRigJoint(joint, joint.lower + fraction*(joint.upper-joint.lower));
  // Resolve mimic chains in dependency order, independent of URDF traversal order.
  for (let pass = 0; pass < rig.length; pass++) for (const j of rig) if (j.mimic) {
    const parent = rig.find(x => x.name === j.mimic.joint);
    if (parent) setRigJoint(j, parent.value*j.mimic.multiplier+j.mimic.offset);
  }
  simulation?.setPositions(rig.map(j => j.value));
  viewer.model.updateMatrixWorld(true); jointUI();
}

function colorModel() {
  const T = viewer?.THREE;
  if (!T || !viewer.model || !details) return;
  const colors = new Map(details.links.map((p,i) => [p.name, new T.Color().setHSL((i*.61803398875)%1,.5,.55)]));
  viewer.model.traverse(object => {
    if (!object.isMesh) return;
    if (!object.userData.gxMaterials) {
      // Own each material before changing it; source GLBs can share materials across links.
      const originals = [].concat(object.material);
      object.userData.gxMaterials = originals.map(material => ({source:material, clone:material.clone()}));
      object.material = Array.isArray(object.material) ? object.userData.gxMaterials.map(m=>m.clone) : object.userData.gxMaterials[0].clone;
    }
    for (const {source,clone} of object.userData.gxMaterials) {
      clone.copy(source);
      if (partColors) {
        clone.color.copy(colors.get(object.userData.rfw_part) || new T.Color('#999'));
        clone.map = null; clone.metalness = 0; clone.roughness = .8;
      }
      if (part && object.userData.rfw_part !== part) { clone.transparent = true; clone.opacity = .18; clone.depthWrite = false; }
      else if (part && clone.emissive) { clone.emissive.setHex(0x3b2d0d); clone.emissiveIntensity = .35; }
      clone.needsUpdate = true;
    }
  });
}

function releaseOriginalMaterials() {
  const seen = new Set();
  viewer?.model?.traverse(object => object.userData.gxMaterials?.forEach(({source}) => {
    if (!seen.has(source)) { seen.add(source); source.dispose(); }
  }));
}

function renderParts() {
  if (!details) return;
  const term = $('#gx-part-search').value.toLowerCase().trim();
  const links = details.links.filter(p => pretty(p.name).toLowerCase().includes(term));
  $('#gx-parts').innerHTML = `<button data-part="" aria-pressed="${part === null}">All parts</button>` + links.map(p => `<button data-part="${escape(p.name)}" aria-pressed="${part === p.name}">${escape(pretty(p.name))}</button>`).join('');
  $$('[data-part]').forEach(button => button.addEventListener('click', () => selectPart(button.dataset.part || null)));
}

function selectPart(name, syncJoint = true) {
  if (!details) return;
  part = name;
  if (syncJoint && name) {
    let link;
    viewer.model.traverse(object => { if (object.userData.rfw_link === name) link = object; });
    for (let node = link; node; node = node.parent) {
      const index = rig.findIndex(j => j.name === node.userData.rfw_joint);
      if (index >= 0) { $('#gx-joint').value = String(index); break; }
    }
  }
  renderParts(); renderInfo(); colorModel(); jointUI();
}

function renderInfo() {
  if (!details) return;
  const target = $('#gx-part-info');
  if (!part) {
    const mass = details.links.reduce((sum,p) => sum+(p.massKg || 0),0);
    const missing = details.links.filter(p=>p.massKg==null).length;
    target.innerHTML = `<h4>Whole asset</h4><p class="gx-part-subtitle">${seedName(selected)} · ${escape(family.name)}</p>${fields([['Parts',details.links.length],['Movable joints',rig.length],[missing?'Recorded link mass':'Link mass total',unit(mass,'kg')],['Surface materials',selected.materialClasses.length]])}<p class="gx-part-description">Select a part below the model to highlight it and inspect its source properties.${missing?` ${missing} parts have no recorded inertial mass.`:''}</p>`;
    return;
  }
  const link = details.links.find(l => l.name === part);
  const surfaces = details.parts.filter(p => p.link === part);
  target.innerHTML = `<h4>${escape(pretty(part))}</h4><p class="gx-part-subtitle">${surfaces.length} visual ${surfaces.length === 1 ? 'surface' : 'surfaces'} · source URDF link</p>${fields([['Part mass',unit(link.massKg,'kg')],['Center of mass',link.centerOfMass?link.centerOfMass.map(number).join(', ')+' m':'—']])}<label class="gx-surface-label" for="gx-surface">Surface material</label><select id="gx-surface">${surfaces.map((p,i)=>`<option value="${i}">${escape(p.name)}</option>`).join('')}</select><div id="gx-surface-info"></div><details class="gx-inertia"><summary>Inertia tensor · kg·m²</summary><p>${link.inertia ? ['ixx','ixy','ixz','ixy','iyy','iyz','ixz','iyz','izz'].map(k=>number(link.inertia[k])).reduce((rows,n,i)=>rows+n+(i%3===2?'<br/>':' · '),'') : 'Not recorded'}</p><small>Source link inertial frame</small></details>`;
  const showSurface = index => {
    const surface = surfaces[index]; if (!surface) return;
    const p = surface.physics;
    $('#gx-surface-info').innerHTML = `<p class="gx-surface-material">Appearance: ${escape(pretty(surface.materialClass).replaceAll('.',' / '))}</p>${p ? `<p class="gx-part-description">Physics material: ${escape(pretty(p.material_subtype||p.material))}</p>`+fields([['Density',unit(p.density,'kg/m³')],['Young’s modulus',unit(p.young_modulus_gpa,'GPa')],['Poisson ratio',number(p.poisson_ratio)],['Restitution',number(p.restitution)],['Static friction',number(p.mu1)],['Dynamic friction',number(p.mu2)]]) : '<p class="gx-part-description">No unambiguous surface-level annotation. Part mass and inertia come directly from the source URDF.</p>'}`;
  };
  $('#gx-surface').addEventListener('change', event => showSurface(Number(event.target.value))); showSurface(0);
}

function renderRecord() {
  const sim = details.simulation;
  $('#gx-record').innerHTML = `<p>Source: PV_A_vlm / ${escape(selected.sourceRelative)}</p><p>Input images: ${family.inputs.map(i=>escape(i.source)).join('; ')}</p><p>Generator SHA-256<br/><code>${escape(selected.templateHash)}</code></p><p>URDF SHA-256<br/><code>${escape(selected.urdfHash)}</code></p><p>Part mass and inertia: source URDF. Surface attributes: source annotations where names or geometric signatures match unambiguously; missing values are shown as —.</p>${sim ? `<p>Simulation: ${escape(sim.engine)}; base fixed. ${escape(sim.collision)}. ${escape(sim.collisionFilter?.description || "")}. ${escape(sim.friction)}. ${escape(sim.inertia)}.</p><p>${escape(sim.interaction?.description || "")} ${escape(sim.interaction?.rule || "")}. Simulation pauses if a joint exceeds 10× its rated speed (or the documented fallback speed).</p><p>${escape(sim.contact)}. ${escape(sim.material)}.</p>${sim.adjustments.length ? `<p>${sim.adjustments.length} source inertia tensor(s) projected to positive, physically valid principal moments; displayed source tensors are unchanged.</p>` : ''}` : ''}<p>Dataset annotations are model parameters, not laboratory measurements.</p>`;
}

async function openAsset(id, scroll = false) {
  const asset = byId.get(id); if (!asset) return;
  if (family?.id !== asset.category) selectFamily(asset.category);
  const ticket = ++version;
  stopSimulation(); loading = true; selected = asset; details = null; rig = []; part = null;
  renderSeeds(); $('#gx-workbench').hidden = false; delete $('#gx-workbench').dataset.loaded;
  $('#gx-asset-title').textContent = asset.name; $('#gx-asset-tag').textContent = `${seedName(asset)} · ${asset.domain}`;
  $('#gx-part-info').innerHTML = ''; $('#gx-parts').innerHTML = ''; $('#gx-joint').innerHTML = '';
  $('#gx-part-search').value = ''; $('#gx-record').innerHTML = ''; $('#gx-share').textContent = 'Copy link';
  for (const button of $$('.gx-actions button')) button.disabled = true;
  status('Loading source asset…'); jointUI();
  if (scroll) $('#gx-workbench').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block:'start'});
  try {
    const [v, info] = await Promise.all([getViewer(),fetch(url(asset.details)).then(r => {if (!r.ok) throw Error('Asset properties could not load.'); return r.json();})]);
    if (ticket !== version) return;
    releaseOriginalMaterials();
    const loaded = await v.load(url(asset.model));
    if (ticket !== version || !loaded) return;
    details = info; configureRig(); loading = false; partColors = false;
    $('#gx-color').setAttribute('aria-pressed','false'); $('#gx-color').textContent='Color parts';
    for (const button of $$('.gx-actions button')) button.disabled = false;
    selectPart(null); renderRecord(); v.resize(); status('');
    $('#gx-workbench').dataset.loaded = id;
    const target = new URL(location.href); target.searchParams.set('sample',id); target.hash='dataset';
    history.replaceState(null,'',target);
  } catch (error) { if (ticket === version) { loading = false; status(`${error.message} Select the preview to retry.`); } }
}

async function enableSimulation() {
  if (loading || !details) return;
  if (simulation) { stopSimulation(); jointUI(); return; }
  const ticket = ++simVersion, assetTicket = version;
  $('#gx-simulate').disabled = true; $('#gx-simulate').textContent = 'Loading physics…';
  try {
    const [{loadSimulation}, xml] = await Promise.all([import('./simulation.js'),fetch(url(selected.simulation)).then(r=>{if(!r.ok) throw Error('Simulation model could not load.');return r.text();})]);
    if (ticket !== simVersion || assetTicket !== version) return;
    const sim = await loadSimulation(xml, selected.joints, details.simulation.interaction);
    if (ticket !== simVersion || assetTicket !== version) { sim.dispose(); return; }
    simulation = sim; sim.setPositions(rig.map(j=>j.value)); sim.gravity($('#gx-gravity').checked);
    sim.stabilize($('#gx-damping').checked); updateSimulationNote(); jointUI();
    $('#gx-simulation').hidden = false; $('#gx-simulate').setAttribute('aria-pressed','true');
    $('#gx-simulate').textContent = 'Exit simulation'; $('#gx-play').textContent='▶ Run'; status('');
  } catch (error) { if (ticket === simVersion && assetTicket === version) { status(`Physics could not start: ${error.message}`); $('#gx-simulate').textContent='Retry simulation'; } }
  finally { if (ticket === simVersion && assetTicket === version) $('#gx-simulate').disabled=false; }
}

$('#gx-search').addEventListener('input',renderCategories);
$('#gx-domain').addEventListener('change',renderCategories);
$('#gx-more').addEventListener('click',()=>{expanded=!expanded;renderCategories();});
$('#gx-part-search').addEventListener('input',renderParts);
$('#gx-joint').addEventListener('change',()=>{const j=rig[Number($('#gx-joint').value)];if(j)selectPart(j.child,false);jointUI();});
$('#gx-position').addEventListener('input',event=>changePosition(Number(event.target.value)/1000));
$('#gx-color').addEventListener('click',()=>{partColors=!partColors;$('#gx-color').setAttribute('aria-pressed',String(partColors));$('#gx-color').textContent=partColors?'Show appearance':'Color parts';colorModel();});
$('#gx-simulate').addEventListener('click',enableSimulation);
$('#gx-play').addEventListener('click',()=>{if(simulation){simulation.running=!simulation.running;jointUI();}});
$('#gx-gravity').addEventListener('change',event=>simulation?.gravity(event.target.checked));
function updateSimulationNote() {
  $('#gx-sim-note').textContent = `MuJoCo · fixed base · ${simulation?.stabilized ? 'added interaction damping' : 'source joint dynamics'}`;
}
$('#gx-damping').addEventListener('change',event=>{simulation?.stabilize(event.target.checked);updateSimulationNote();jointUI();});
$('#gx-force-minus').addEventListener('click',()=>simulation?.push(Number($('#gx-joint').value),-1));
$('#gx-force-plus').addEventListener('click',()=>simulation?.push(Number($('#gx-joint').value),1));
$('#gx-reset').addEventListener('click',()=>{simulation?.reset();rig.forEach(j=>setRigJoint(j,0));viewer?.reset();jointUI();status('');});
$('#gx-share').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(location.href);$('#gx-share').textContent='Copied';}catch{$('#gx-share').textContent='Use address-bar link';}});
$('#gx-input-enlarge').addEventListener('click',()=>{const dialog=$('#figure-dialog'),source=$('#gx-input-image');dialog.querySelector('img').src=source.src;dialog.querySelector('img').alt=source.alt;dialog.showModal();});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&simulation)simulation.running=false;});
new IntersectionObserver(([entry])=>{if(!entry.isIntersecting&&simulation)simulation.running=false;}).observe($('#gx-workbench'));

window.rfwExplorer = {openAsset, selectFamily, selectPart, enableSimulation,
  get viewer(){return viewer;},get simulation(){return simulation;},get rig(){return rig;},
  get selected(){return selected;},get details(){return details;},get manifest(){return manifest;}};
fetch(url('data/explorer.json')).then(r=>{if(!r.ok)throw Error('unavailable');return r.json();}).then(data=>{
  const featured=['Music_Headphone','Chair_Folding_chair','Handtools_Clamp','Sports_Roller_scates','Technology_Laptop','Sports_Table_football','Handtools_dial_caliper','Light_Latern','Other_Folding_screen','Accessories_glasses','Handtools_Stapler','Technology_Graphics_Card','Bag_Suitcase_Treasure_chest','Others_Binocular','Headwear_Racing_helmet'];
  data.families.sort((a,b)=>(featured.includes(a.id)?featured.indexOf(a.id):100)-(featured.includes(b.id)?featured.indexOf(b.id):100));
  manifest=data;byId=new Map(data.assets.map(a=>[a.id,a]));
  $('#gx-domain').innerHTML='<option value="all">All categories</option>'+[...new Set(data.families.map(f=>f.domain))].sort().map(d=>`<option>${escape(d)}</option>`).join('');
  selectFamily(data.families[0].id);
  const sample=new URLSearchParams(location.search).get('sample');
  if(byId.has(sample))openAsset(sample);
}).catch(()=>{$('#gx-count').textContent='The asset catalog could not load. Reload to try again.';});
