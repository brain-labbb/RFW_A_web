import './dataset.js';
import './style.css';
import {scenes,edits,tasks,scaleRows,qualityRows,transferRows} from './data.js';
const $=(s)=>document.querySelector(s), $$=(s)=>[...document.querySelectorAll(s)];
const base=import.meta.env.BASE_URL;
const url=p=>base+p;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const videoExtension=document.createElement('video').canPlayType('video/mp4; codecs="avc1.42E01E"')?'mp4':'webm';
const videoUrl=name=>url(`media/${name}.${videoExtension}`);
if(videoExtension==='webm')$$('video').forEach(v=>{const source=v.getAttribute('src')||v.querySelector('source')?.getAttribute('src');if(source)v.src=source.replace(/\.mp4$/,'.webm');});
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
const selectTab=(buttons,chosen)=>buttons.forEach(b=>{b.setAttribute('aria-selected',String(b===chosen));b.tabIndex=b===chosen?0:-1;});
$$('[role=tab]').forEach(b=>b.tabIndex=b.getAttribute('aria-selected')==='true'?0:-1);
// Keyboard navigation for all tab groups.
$$('[role=tablist]').forEach(list=>list.addEventListener('keydown',e=>{
 const tabs=[...list.querySelectorAll('[role=tab]')],idx=tabs.indexOf(document.activeElement);if(idx<0)return;
 let next;if(e.key==='ArrowRight')next=(idx+1)%tabs.length;else if(e.key==='ArrowLeft')next=(idx+tabs.length-1)%tabs.length;else if(e.key==='Home')next=0;else if(e.key==='End')next=tabs.length-1;else return;
 e.preventDefault();tabs[next].focus();tabs[next].click();
}));
$('.menu-toggle').addEventListener('click',()=>{const open=$('.header nav').classList.toggle('open');$('.menu-toggle').setAttribute('aria-expanded',open);});
$$('.header nav a').forEach(a=>a.addEventListener('click',()=>{$('.header nav').classList.remove('open');$('.menu-toggle').setAttribute('aria-expanded','false');}));

const video=$('#scene-video'),scenePlay=$('#scene-play');
function updateSceneButton(){scenePlay.innerHTML=video.paused?'▶ <span>Play scene</span>':'Ⅱ <span>Pause scene</span>';scenePlay.setAttribute('aria-label',video.paused?'Play scene video':'Pause scene video');}
video.addEventListener('play',updateSceneButton);video.addEventListener('pause',updateSceneButton);
scenePlay.addEventListener('click',()=>video.paused?video.play().catch(()=>{}):video.pause());
$$('[data-scene]').forEach(b=>b.addEventListener('click',()=>{
 const s=b.dataset.scene,data=scenes[s];selectTab($$('[data-scene]'),b);video.pause();video.poster=url(`media/${s}.webp`);video.src=videoUrl(s);video.load();
 $('#scene-index').textContent=`${data.index} / 04`;$('#scene-title').innerHTML=data.title;$('#scene-subtitle').textContent=data.subtitle;video.setAttribute('aria-label',`${s} articulated scene`);
 if(!reduced)video.play().catch(()=>{});updateSceneButton();
 setFilter(s);
}));
const videoObserver=new IntersectionObserver(entries=>entries.forEach(e=>{if(!e.isIntersecting)e.target.pause();}),{threshold:0.05});$$('video').forEach(v=>videoObserver.observe(v));
// Dialogs retain native focus trapping and Escape behavior.
const film=$('#film-dialog');$$('.film-open').forEach(b=>b.addEventListener('click',()=>{film.showModal();film.querySelector('video').play().catch(()=>{});}));film.addEventListener('close',()=>film.querySelector('video').pause());film.addEventListener('cancel',()=>film.querySelector('video').pause());
$$('dialog').forEach(d=>{d.querySelector('.dialog-close').addEventListener('click',()=>d.close());d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}});});
$$('[data-lightbox]').forEach(b=>b.addEventListener('click',()=>{const d=$('#figure-dialog');d.querySelector('img').src=url(b.dataset.lightbox);d.querySelector('img').alt=b.dataset.caption;d.querySelector('p').textContent=b.dataset.caption;d.showModal();}));

let catalog=[],selected=null,filter='all',viewer=null,viewerPromise=null,selectionVersion=0,infoTab='structure';
function setFilter(value){filter=value;$$('[data-filter]').forEach(b=>{b.classList.toggle('active',b.dataset.filter===value);b.setAttribute('aria-pressed',b.dataset.filter===value);});renderCatalog();}
$$('[data-filter]').forEach(b=>b.addEventListener('click',()=>setFilter(b.dataset.filter)));$('#asset-search').addEventListener('input',renderCatalog);
function renderCatalog(){
 const term=$('#asset-search').value.trim().toLowerCase();const assets=catalog.filter(a=>(filter==='all'||a.scene===filter)&&(a.name+' '+a.scene).toLowerCase().includes(term));
 $('#asset-count').textContent=`${assets.length} / 84 SCENE ASSETS`;
 $('#asset-grid').innerHTML=assets.length?assets.map(a=>`<button class="asset-card ${a.id===selected?.id?'selected':''}" data-id="${a.id}" aria-pressed="${a.id===selected?.id}"><img src="${url(a.thumbnail)}" alt="" loading="lazy" width="300" height="240"/><h4>${esc(a.name)}</h4><span>${a.joints.filter(j=>j.type!=='fixed').length} JOINTS · ${a.scene==='laboratory'?'LAB':a.scene.toUpperCase()}</span></button>`).join(''):'<p class="empty-results">No matching assets. Try another name or scene.</p>';
 $$('.asset-card').forEach(b=>b.addEventListener('click',()=>selectAsset(catalog.find(a=>a.id===b.dataset.id))));
}
async function getViewer(){
 if(!viewerPromise)viewerPromise=import('./viewer.js').then(({AssetViewer})=>{
  viewer=new AssetViewer($('#model-viewer'),(f,t)=>{$('#motion-progress').value=String(Math.round(f*1000));$('#motion-time').textContent=t.toFixed(1)+' s';});
  return viewer;
 });return viewerPromise;
}
function playState(playing){$('#motion-play').textContent=playing?'Ⅱ':'▶';$('#motion-play').setAttribute('aria-label',playing?'Pause asset motion':'Play asset motion');}
async function selectAsset(asset){
 if(!asset)return;const version=++selectionVersion;selected=asset;renderCatalog();$('#asset-name').textContent=asset.name;$('#asset-scene-label').textContent=`${asset.scene.toUpperCase()} / ARTICULATED OBJECT`;
 $('#viewer-status').hidden=false;$('#viewer-status').textContent='Loading 3D asset…';playState(false);$('#motion-play').disabled=true;$('#motion-progress').disabled=true;renderAssetInfo();
 try{const v=await getViewer();const loaded=await v.load(url(asset.model));if(version!==selectionVersion||!loaded)return;$('#viewer-status').hidden=true;$('#motion-play').disabled=!v.duration;$('#motion-progress').disabled=!v.duration;window.__viewerReady=asset.id;}
 catch(e){if(version!==selectionVersion)return;$('#viewer-status').textContent='3D preview could not load. Select another asset or reload to try again.';console.error('Model loading failed',e);}
}
$('#motion-play').addEventListener('click',()=>{if(viewer)playState(viewer.setPlaying(!viewer.playing));});
$('#motion-progress').addEventListener('input',e=>{if(viewer){viewer.setPlaying(false);playState(false);viewer.seek(Number(e.target.value)/1000);}});
$('#viewer-reset').addEventListener('click',()=>{if(viewer){viewer.setPlaying(false);playState(false);viewer.reset();}});
$$('[data-info]').forEach(b=>b.addEventListener('click',()=>{selectTab($$('[data-info]'),b);infoTab=b.dataset.info;viewer?.highlightMaterial(null);renderAssetInfo();}));
const physicsCache=new Map();
async function renderAssetInfo(){
 if(!selected)return;const a=selected;
 if(infoTab==='structure'){
  const types={};for(const j of a.joints)types[j.type]=(types[j.type]||0)+1;
  $('#asset-info').innerHTML=`<div class="info-summary"><div><span>MOVABLE JOINTS</span><strong>${a.joints.filter(j=>j.type!=='fixed').length}</strong></div><div><span>MESH OBJECTS</span><strong>${a.meshes}</strong></div><div><span>SCENE UNITS</span><strong>meters</strong></div></div><div class="joint-chips">${Object.entries(types).map(([k,v])=>`<span>${v} ${esc(k)}</span>`).join('')}</div><details class="joint-limits"><summary>Joint limits (${a.joints.length} controllers)</summary><dl>${a.joints.map(j=>`<dt>${esc(j.name)}</dt><dd>${j.type==='continuous'?'continuous':j.lower!=null&&j.upper!=null?`${Number(j.lower).toFixed(2)} → ${Number(j.upper).toFixed(2)} ${j.type==='prismatic'?'m':'rad'}`:'—'}</dd>`).join('')}</dl></details>`;
 }else{
  $('#asset-info').innerHTML='<p class="note">Loading material properties…</p>';
  try{
   if(!physicsCache.has(a.id)){const r=await fetch(url(`data/physics/${a.id}.json`));if(!r.ok)throw Error('Unavailable');physicsCache.set(a.id,await r.json());}
   if(selected.id!==a.id||infoTab!=='materials')return;
   const data=physicsCache.get(a.id);
   $('#asset-info').innerHTML=`<label class="sr-only" for="material-select">Material and associated parts</label><select id="material-select" class="material-select">${data.materials.map((m,i)=>`<option value="${i}">${esc(m.material)} · ${m.parts.length} mesh${m.parts.length===1?'':'es'}</option>`).join('')}</select><p class="material-parts" id="material-parts"></p><div class="physics-grid" id="physics-values"></div>`;
   const show=i=>{const m=data.materials[i],v=m.values;$('#material-parts').textContent=m.parts.slice(0,4).map(p=>p.split(' / ').pop().replaceAll('_',' ')).join(' · ')+(m.parts.length>4?` · +${m.parts.length-4} more`:'');$('#physics-values').innerHTML=[['Density',Number(v.density_kg_m3).toLocaleString()+' kg/m³'],['Young’s modulus',(v.youngs_modulus_pa/1e9).toPrecision(3)+' GPa'],['Poisson’s ratio',v.poissons_ratio],['Static friction',v.static_friction_coefficient],['Dynamic friction',v.dynamic_friction_coefficient],['Restitution',v.restitution_coefficient]].map(([k,val])=>`<div><small>${k}</small>${val}</div>`).join('');viewer?.highlightMaterial(m.surfaceMaterial);};
   $('#material-select').addEventListener('change',e=>show(Number(e.target.value)));show(0);
  }catch{$('#asset-info').innerHTML='<p class="note">Material properties are not available for this asset.</p>';}
 }
}
// Small public interface also drives reproducible thumbnail generation and browser checks.
window.rfw={selectAsset:async id=>selectAsset(catalog.find(a=>a.id===id)),get viewer(){return viewer;},get catalog(){return catalog;}};
fetch(url('data/catalog.json')).then(r=>{if(!r.ok)throw Error('Catalog unavailable');return r.json();}).then(data=>{catalog=data;renderCatalog();const id=new URLSearchParams(location.search).get('asset');return selectAsset(catalog.find(a=>a.id===id)||catalog[0]);}).catch(()=>{$('#asset-grid').innerHTML='<p class="empty-results">The asset catalog could not load. Please reload the page.</p>';});

$('#sample-count').addEventListener('input',e=>{const n=Number(e.target.value),cost=10.62/n;$('#sample-output').textContent=n.toLocaleString();$('#our-cost').textContent='$'+cost.toFixed(cost<1?3:2);$('#our-cost-bar').style.width=Math.min(100,cost/Math.max(1.237,cost)*100)+'%';$('.cost-row:not(.ours) .cost-track i').style.width=(1.237/Math.max(1.237,cost)*100)+'%';});
let activeEdit='component';
function renderEdit(kind){
 activeEdit=kind;const e=edits[kind];$('#edit-title').textContent=e.title;$('#edit-description').textContent=e.description;$('#edit-before').src=url(`media/edit-${e.folder}-${e.files[0]}.webp`);$('#edit-before').alt=e.labels[0]+' reference configuration';$('#edit-before-caption').textContent=e.labels[0];
 $('#edit-options').innerHTML='<legend class="sr-only">Select a configuration</legend>'+e.labels.map((v,i)=>`<button data-variant="${i}" aria-pressed="false">${v}</button>`).join('');
 $$('#edit-options button').forEach(b=>b.addEventListener('click',()=>setVariant(Number(b.dataset.variant))));setVariant(1);
}
function setVariant(i){const e=edits[activeEdit];$('#edit-after').src=url(`media/edit-${e.folder}-${e.files[i]}.webp`);$('#edit-after').alt=e.labels[i]+' edited configuration';$('#edit-after-caption').textContent=e.labels[i];$('#edit-code').textContent=`${e.key} = ${JSON.stringify(e.values[i])}`;$$('#edit-options button').forEach((b,j)=>b.setAttribute('aria-pressed',String(i===j)));}
$$('[data-edit]').forEach(b=>b.addEventListener('click',()=>{selectTab($$('[data-edit]'),b);renderEdit(b.dataset.edit);}));renderEdit('component');
let result='scale',sortColumn=null,sortDescending=true;
function renderResults(){
 let heads,rows,note;
 if(result==='scale'){heads=['Dataset','Assets ↑','Categories','Mean joints','Multi-joint % ↑','nTED ↑'];rows=scaleRows;note='Paper Tables 1–2. Joint statistics use successfully parsed assets. nTED is averaged over all pairs of 250 valid trees per source, including cross-category pairs. Mean joint count is descriptive. Seven evaluated baseline datasets are shown.';}
 else if(result==='validity'){heads=['Dataset','Resource resolution % ↑','Non-degeneracy % ↑','Kinematic pass % ↑','Import % ↑','Stable rollout % ↑'];rows=qualityRows;note='Paper Table 3. Resource resolution, non-degeneracy, and kinematic validity use full releases; non-degeneracy is joint-level. Import and 1-second stable rollout use Core-200 and require a pass in all four simulators. These tests do not certify all possible motions.';}
 else{heads=['Training data','Rest mIoU ↑','Rest gIoU ↑','Rest PC ↓','Art. gIoU ↑','Art. PC ↓','Art. OC ↓'];rows=transferRows[$('#split-select').value];note='Paper Table 4. PM = PartNet-Mobility. PC and OC denote part-level and object-level Chamfer distances. Category OOD evaluates unseen categories. RFW-A improves part-level metrics; its OOD object-level Chamfer is slightly worse than PM + Articraft (0.02403 vs. 0.02343).';}
 rows=rows.map(r=>[...r]);if(sortColumn!==null)rows.sort((a,b)=>(typeof a[sortColumn]==='string'?a[sortColumn].localeCompare(b[sortColumn]):a[sortColumn]-b[sortColumn])*(sortDescending?-1:1));
 $('#split-control').hidden=result!=='transfer';$('#results-note').textContent=note;
 $('#results-table').innerHTML=`<thead><tr>${heads.map((h,i)=>`<th scope="col" aria-sort="${sortColumn===i?(sortDescending?'descending':'ascending'):'none'}"><button data-sort="${i}">${h}${sortColumn===i?(sortDescending?' ▾':' ▴'):''}</button></th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr class="${row[0].includes('RFW')?'ours':''}">${row.map((v,i)=>i===0?`<th scope="row">${esc(v)}</th>`:`<td>${result==='transfer'?v.toFixed(5):result==='scale'&&i===1?v.toLocaleString():v}</td>`).join('')}</tr>`).join('')}</tbody>`;
 $$('#results-table [data-sort]').forEach(b=>b.addEventListener('click',()=>{const c=Number(b.dataset.sort);sortDescending=sortColumn===c?!sortDescending:true;sortColumn=c;renderResults();}));
}
$$('[data-result]').forEach(b=>b.addEventListener('click',()=>{selectTab($$('[data-result]'),b);result=b.dataset.result;sortColumn=null;renderResults();}));$('#split-select').addEventListener('change',renderResults);renderResults();
const sim=$('#sim-video'),real=$('#real-video');
$$('[data-task]').forEach(b=>b.addEventListener('click',()=>{selectTab($$('[data-task]'),b);const task=b.dataset.task;for(const [v,suffix] of [[sim,'sim'],[real,'real']]){v.pause();v.poster=url(`media/${task}_${suffix}.webp`);v.src=videoUrl(`${task}_${suffix}`);v.load();}$('#task-description').textContent=tasks[task];$('#play-pair').innerHTML='Play both videos <span>▶</span>';}));
$('#play-pair').addEventListener('click',()=>{if(sim.paused||real.paused){sim.currentTime=0;real.currentTime=0;Promise.allSettled([sim.play(),real.play()]);$('#play-pair').innerHTML='Pause both videos <span>Ⅱ</span>';}else{sim.pause();real.pause();$('#play-pair').innerHTML='Play both videos <span>▶</span>';}});
fetch(url('data/paper.json')).then(r=>r.json()).then(p=>{
 const supers=s=>s.replaceAll('\\dagger','†').replaceAll('\\ddagger','‡');
 $('#author-details').innerHTML=`<p>${p.authors.map(([n,a])=>`${esc(a)}<sup>${esc(supers(n))}</sup>`).join(' · ')}</p><p class="affiliations">${p.affiliations.map(([n,a])=>`<sup>${n}</sup> ${esc(a)}`).join(' &nbsp;·&nbsp; ')}<br/>* Equal contribution &nbsp; † Project leader &nbsp; ‡ Corresponding authors</p>`;$('#abstract-text').textContent=p.abstract;$('#hero-abstract-text').textContent=p.abstract;
}).catch(()=>{});
fetch(url('data/resources.json')).then(r=>r.json()).then(resources=>{for(const [key,href]of Object.entries(resources)){if(!href||!/^https:\/\//.test(href))continue;$$('.resource-links button').filter(b=>b.textContent.toLowerCase().startsWith(key)).forEach(b=>{const a=document.createElement('a');a.href=href;a.target='_blank';a.rel='noopener';a.textContent=key[0].toUpperCase()+key.slice(1)+' ↗';b.replaceWith(a);});}}).catch(()=>{});

const citationButton=document.querySelector('#copy-citation');if(citationButton){citationButton.addEventListener('click',async()=>{const text=document.querySelector('#citation-text').textContent;try{await navigator.clipboard.writeText(text);citationButton.textContent='Copied';setTimeout(()=>citationButton.textContent='Copy BibTeX',1400);}catch{citationButton.textContent='Select to copy';}});}
