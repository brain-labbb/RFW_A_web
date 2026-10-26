import './style.css';
import {AssetViewer} from './viewer.js';
const base=import.meta.env.BASE_URL;const url=p=>base+p;const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];
let catalog=[],filter='all',term='',selected=null,detail='structure',viewer=null,physicsCache=new Map(),request=0;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function sceneName(s){return s==='indoor'?'Indoor':s==='outdoor'?'Outdoor':s==='space'?'Space':'Laboratory';}
function renderList(){
 const matches=catalog.filter(a=>(filter==='all'||a.scene===filter)&&(a.name+' '+a.scene).toLowerCase().includes(term));
 $('#demo-list').innerHTML=matches.length?matches.map(a=>`<button class="demo-item ${selected?.id===a.id?'active':''}" data-id="${a.id}"><img src="${url(a.thumbnail)}" alt="" loading="lazy"/><strong>${esc(a.name)}</strong><small>${a.joints.filter(j=>j.type!=='fixed').length} JOINTS</small></button>`).join(''):'<p class="demo-empty">No matching assets.</p>';
 $$('.demo-item').forEach(b=>b.addEventListener('click',()=>selectAsset(catalog.find(a=>a.id===b.dataset.id))));
}
function sceneButtons(){
 $$('.demo-scene').forEach(b=>{b.classList.toggle('active',b.dataset.scene===filter);b.setAttribute('aria-selected',b.dataset.scene===filter);});
 $('#demo-scene-label').textContent=`${filter==='all'?'ALL SCENES':sceneName(filter).toUpperCase()} / NATIVE ASSETS`;
}
function renderDetails(){
 if(!selected)return;const a=selected;
 if(detail==='structure'){
  const movable=a.joints.filter(j=>j.type!=='fixed'),types={};for(const j of movable)types[j.type]=(types[j.type]||0)+1;
  $('#demo-details').innerHTML=`<div class="info-summary"><div><span>MOVABLE JOINTS</span><strong>${movable.length}</strong></div><div><span>MESH OBJECTS</span><strong>${a.meshes}</strong></div><div><span>SCENE</span><strong>${sceneName(a.scene)}</strong></div><div><span>UNITS</span><strong>meters</strong></div></div><div class="joint-chips">${Object.entries(types).map(([k,v])=>`<span>${v} ${esc(k)}</span>`).join('')}</div><details class="joint-limits"><summary>Joint limits (${a.joints.length} controllers)</summary><dl>${a.joints.map(j=>`<dt>${esc(j.name)}</dt><dd>${j.type==='continuous'?'continuous':j.lower!=null&&j.upper!=null?`${Number(j.lower).toFixed(2)} → ${Number(j.upper).toFixed(2)} ${j.type==='prismatic'?'m':'rad'}`:'—'}</dd>`).join('')}</dl></details>`;
 }else{
  $('#demo-details').innerHTML='<p class="demo-empty">Loading material properties…</p>';
  loadPhysics(a).then(data=>{if(selected?.id!==a.id||detail!=='materials')return;$('#demo-details').innerHTML=`<select id="demo-material" class="material-select">${data.materials.map((m,i)=>`<option value="${i}">${esc(m.material)} · ${m.parts.length} meshes</option>`).join('')}</select><p class="material-parts" id="demo-material-parts"></p><div class="physics-grid" id="demo-physics"></div>`;const show=i=>{const m=data.materials[i],v=m.values;$('#demo-material-parts').textContent=m.parts.slice(0,6).map(p=>p.split(' / ').pop().replaceAll('_',' ')).join(' · ')+(m.parts.length>6?` · +${m.parts.length-6} more`:'');$('#demo-physics').innerHTML=[['Density',Number(v.density_kg_m3).toLocaleString()+' kg/m³'],['Young’s modulus',(v.youngs_modulus_pa/1e9).toPrecision(3)+' GPa'],['Poisson’s ratio',v.poissons_ratio],['Static friction',v.static_friction_coefficient],['Dynamic friction',v.dynamic_friction_coefficient],['Restitution',v.restitution_coefficient]].map(([k,x])=>`<div><small>${k}</small>${x}</div>`).join('');viewer?.highlightMaterial(m.surfaceMaterial);};$('#demo-material').addEventListener('change',e=>show(Number(e.target.value)));show(0);}).catch(()=>{$('#demo-details').innerHTML='<p class="demo-empty">Material properties are unavailable for this asset.</p>';});
 }
}
async function loadPhysics(a){if(!physicsCache.has(a.id)){const r=await fetch(url(`data/physics/${a.id}.json`));if(!r.ok)throw Error('unavailable');physicsCache.set(a.id,await r.json());}return physicsCache.get(a.id);}
async function selectAsset(a){if(!a)return;selected=a;const version=++request;renderList();$('#demo-asset-name').textContent=a.name;$('#demo-loading').hidden=false;$('#demo-loading').textContent='Loading native geometry…';$('#demo-play').disabled=true;$('#demo-progress').disabled=true;renderDetails();try{if(!viewer)viewer=new AssetViewer($('#demo-viewer'),(f,t)=>{$('#demo-progress').value=Math.round(f*1000);$('#demo-time').textContent=t.toFixed(1)+' s';});const ok=await viewer.load(url(a.model));if(version!==request||!ok)return;$('#demo-loading').hidden=true;$('#demo-play').disabled=!viewer.duration;$('#demo-progress').disabled=!viewer.duration;}catch(e){$('#demo-loading').textContent='This asset could not load.';console.error(e);}}
$$('.demo-scene').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.scene;sceneButtons();renderList();}));$('#demo-search').addEventListener('input',e=>{term=e.target.value.toLowerCase();renderList();});
$$('[data-detail]').forEach(b=>b.addEventListener('click',()=>{detail=b.dataset.detail;$$('[data-detail]').forEach(x=>x.setAttribute('aria-selected',String(x===b)));renderDetails();}));
$('#demo-play').addEventListener('click',()=>{if(viewer){const playing=viewer.setPlaying(!viewer.playing);$('#demo-play').textContent=playing?'Ⅱ':'▶';$('#demo-play').setAttribute('aria-label',playing?'Pause asset motion':'Play asset motion');}});$('#demo-progress').addEventListener('input',e=>{viewer?.setPlaying(false);if(viewer)viewer.seek(Number(e.target.value)/1000);$('#demo-play').textContent='▶';});$('#demo-reset').addEventListener('click',()=>{viewer?.reset();viewer?.setPlaying(false);$('#demo-play').textContent='▶';});
fetch(url('data/catalog.json')).then(r=>r.json()).then(data=>{catalog=data;sceneButtons();renderList();selectAsset(catalog[0]);}).catch(()=>{$('#demo-list').innerHTML='<p class="demo-empty">The catalog could not load.</p>';});
