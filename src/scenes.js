const $=s=>document.querySelector(s),base=import.meta.env.BASE_URL,url=p=>base+p;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
let data,catalog,scene='indoor',selected,property='materials',version=0,visible=false;
const cache=new Map(),detail=$('#scene-detail-video'),overview=$('#scene-video'),stage=$('.scene-map');
function movieMode(){stage.classList.toggle('is-playing',!overview.paused);$('#scene-hotspots').inert=!overview.paused;}
overview.addEventListener('play',movieMode);overview.addEventListener('pause',movieMode);
function setScene(id){
 scene=id;const d=data.find(s=>s.id===id);$('#scene-map-image').src=url(d.image);$('#scene-map-image').alt=`${d.label} scene. Select a highlighted object.`;$('#scene-map-caption').textContent=`${d.label} · Select a highlighted object`;$('#scene-browse').href=url(`demo.html?scene=${id}`);
 $('#scene-hotspots').innerHTML=`<svg viewBox="0 0 960 540" aria-hidden="true">${d.objects.map(a=>`<polygon data-scene-shape="${a.id}" points="${a.polygon.map(([x,y])=>`${x*960},${y*540}`).join(' ')}"/>`).join('')}</svg>`+d.objects.map((a,i)=>`<button class="scene-pin" data-scene-object="${a.id}" style="left:${a.pin[0]*100}%;top:${a.pin[1]*100}%" aria-label="${i+1}. ${esc(a.name)}" aria-pressed="false"><span>${i+1}</span><span class="pin-label">${esc(a.name)}</span></button>`).join('');
 $('#scene-object-choices').innerHTML=d.objects.map((a,i)=>`<button data-scene-object="${a.id}" aria-pressed="false"><span>${i+1}</span>${esc(a.name)}</button>`).join('');
 document.querySelectorAll('[data-scene-object]').forEach(b=>b.addEventListener('click',()=>select(d.objects.find(a=>a.id===b.dataset.sceneObject),true)));
 document.querySelectorAll('[data-scene-shape]').forEach(b=>b.addEventListener('click',()=>select(d.objects.find(a=>a.id===b.dataset.sceneShape),true)));
 select(d.objects[0],false);
}
function select(a,play){
 selected=a;document.querySelectorAll('[data-scene-object]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.sceneObject===a.id)));document.querySelectorAll('[data-scene-shape]').forEach(b=>b.classList.toggle('selected',b.dataset.sceneShape===a.id));
 detail.pause();detail.poster=url(a.poster);detail.src=url(a.video.replace('.mp4',detail.canPlayType('video/mp4; codecs="avc1.42E01E"')?'.mp4':'.webm'));detail.load();detail.setAttribute('aria-label',`${a.name}: camera walkthrough in the ${scene} scene`);
 $('#scene-object-title').textContent=a.name;$('#scene-object-context').textContent=scene.toUpperCase();const c=catalog.find(c=>c.id===a.id),joints=c.joints.filter(j=>j.type!=='fixed').length;$('#scene-object-summary').textContent=`${joints} movable ${joints===1?'joint':'joints'} · ${c.meshes} mesh objects`;$('#scene-object-3d').href=url(`demo.html?asset=${a.id}`);$('.scene-inspector').dataset.selected=a.id;$('#scene-live-status').textContent=`${a.name} selected. Its close-up and properties are shown beside the scene.`;renderProperties();
 if(play&&!reduced&&visible)detail.play().catch(()=>{});
}
async function renderProperties(){
 if(!selected)return;const a=catalog.find(c=>c.id===selected.id),v=++version;const box=$('#scene-object-properties');
 if(property==='joints'){
  box.innerHTML=`<div class="scene-joint-scroll" tabindex="0"><table><thead><tr><th>Joint</th><th>Type / limits</th></tr></thead><tbody>${a.joints.filter(j=>j.type!=='fixed').map(j=>`<tr><td>${esc(j.name)}</td><td>${esc(j.type)}<small>${j.type==='continuous'?'Free rotation':j.lower!=null&&j.upper!=null?`${Number(j.lower).toFixed(2)} → ${Number(j.upper).toFixed(2)} ${j.type==='prismatic'?'m':'rad'}`:'—'}</small></td></tr>`).join('')}</tbody></table></div>`;return;
 }
 box.innerHTML='<p class="note">Loading material properties…</p>';
 try{
  if(!cache.has(a.id)){const r=await fetch(url(`data/physics/${a.id}.json`));if(!r.ok)throw Error('Unavailable');cache.set(a.id,await r.json());}
  if(v!==version)return;const mats=cache.get(a.id).materials;box.innerHTML=`<label class="sr-only" for="scene-material">Material group</label><select id="scene-material">${mats.map((m,i)=>`<option value="${i}">${esc(m.material)}</option>`).join('')}</select><div id="scene-physical-values" class="physics-grid"></div>`;
  const show=i=>{const p=mats[i].values;$('#scene-physical-values').innerHTML=[['Density',p.density_kg_m3.toLocaleString()+' kg/m³'],['Young’s modulus',(p.youngs_modulus_pa/1e9).toPrecision(3)+' GPa'],['Poisson’s ratio',p.poissons_ratio],['Static friction',p.static_friction_coefficient],['Dynamic friction',p.dynamic_friction_coefficient],['Restitution',p.restitution_coefficient]].map(([k,x])=>`<div><small>${k}</small>${x}</div>`).join('');};$('#scene-material').addEventListener('change',e=>show(Number(e.target.value)));show(0);
 }catch{if(v===version)box.innerHTML='<p>Properties could not load. Select this object to retry.</p>';}
}
document.querySelectorAll('[data-scene-property]').forEach(b=>b.addEventListener('click',()=>{property=b.dataset.sceneProperty;document.querySelectorAll('[data-scene-property]').forEach(x=>{x.setAttribute('aria-selected',String(x===b));x.tabIndex=x===b?0:-1;});renderProperties();}));
$('#scene-replay').addEventListener('click',()=>{detail.currentTime=0;detail.play().catch(()=>{});});
new IntersectionObserver(([e])=>{visible=e.isIntersecting;if(!visible)detail.pause();},{threshold:.1}).observe(detail);
document.addEventListener('visibilitychange',()=>{if(document.hidden){detail.pause();overview.pause();}});
Promise.all([fetch(url('data/scenes.json')).then(r=>{if(!r.ok)throw Error('Scene data');return r.json();}),fetch(url('data/catalog.json')).then(r=>r.json())]).then(([d,c])=>{data=d;catalog=c;setScene(scene);document.querySelectorAll('.scene-picker [data-scene]').forEach(b=>b.addEventListener('click',()=>setScene(b.dataset.scene)));}).catch(()=>{$('#scene-object-choices').textContent='Scene exploration could not load. Please reload to try again.';});
