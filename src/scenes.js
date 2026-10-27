const $=s=>document.querySelector(s),base=import.meta.env.BASE_URL,url=p=>base+p;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
let data,catalog,scene='indoor',selected,property='materials',version=0,visible=false;
const cache=new Map(),detail=$('#scene-detail-video'),overview=$('#scene-video'),stage=$('.scene-map');
function movieMode(){stage.classList.toggle('is-playing',!overview.paused);$('#scene-hotspots').inert=!overview.paused;}
overview.addEventListener('play',movieMode);overview.addEventListener('pause',movieMode);
function polygonArea(p){return Math.abs(p.reduce((sum,a,i)=>{const b=p[(i+1)%p.length];return sum+a[0]*b[1]-b[0]*a[1];},0))/2;}
function setScene(id){
 scene=id;const d=data.find(s=>s.id===id);$('#scene-map-image').src=url(d.image);$('#scene-map-image').alt=`${d.label} scene. Select a highlighted object.`;$('#scene-map-caption').textContent=`${d.label} · ${d.objects.length} objects to explore`;const browse=$('#scene-browse');if(browse)browse.href=url(`demo.html?scene=${id}`);
 $('#scene-hotspots').innerHTML=`<svg viewBox="0 0 960 540" aria-hidden="true">${[...d.objects].sort((a,b)=>polygonArea(b.polygon)-polygonArea(a.polygon)).map(a=>`<polygon data-scene-shape="${a.id}" points="${a.polygon.map(([x,y])=>`${x*960},${y*540}`).join(' ')}"/>`).join('')}</svg>`+d.objects.map((a,i)=>`<button class="scene-pin" data-scene-object="${a.id}" style="left:${a.pin[0]*100}%;top:${a.pin[1]*100}%" aria-label="${i+1}. ${esc(a.name)}" aria-pressed="false"><span>${i+1}</span><span class="pin-label">${esc(a.name)}</span></button>`).join('');
 $('#scene-object-choices').innerHTML=d.objects.map((a,i)=>`<button data-scene-object="${a.id}" aria-pressed="false"><span>${i+1}</span>${esc(a.name)}</button>`).join('');
 document.querySelectorAll('[data-scene-object]').forEach(b=>b.addEventListener('click',()=>select(d.objects.find(a=>a.id===b.dataset.sceneObject),true)));
 document.querySelectorAll('[data-scene-shape]').forEach(b=>b.addEventListener('click',()=>select(d.objects.find(a=>a.id===b.dataset.sceneShape),true)));
 select(d.objects[0],false);
}
function select(a,play){
 selected=a;document.querySelectorAll('[data-scene-object]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.sceneObject===a.id)));document.querySelectorAll('[data-scene-shape]').forEach(b=>b.classList.toggle('selected',b.dataset.sceneShape===a.id));
 detail.pause();detail.poster=url(a.poster);detail.src=url(a.video.replace('.mp4',detail.canPlayType('video/mp4; codecs="avc1.42E01E"')?'.mp4':'.webm'));detail.load();detail.setAttribute('aria-label',`${a.name}: camera walkthrough in the ${scene} scene`);
 $('#scene-object-mass').textContent='—';$('#scene-object-title').textContent=a.name;$('#scene-object-context').textContent=scene.toUpperCase();const c=catalog.find(c=>c.id===a.id),joints=c.joints.filter(j=>j.type!=='fixed').length;$('#scene-object-summary').textContent=`${joints} movable ${joints===1?'joint':'joints'} · ${c.meshes} mesh objects`;const link3d=$('#scene-object-3d');if(link3d)link3d.href=url(`demo.html?asset=${a.id}`);$('.scene-inspector').dataset.selected=a.id;$('#scene-live-status').textContent=`${a.name} selected. Its close-up and properties are shown beside the scene.`;renderProperties();
 if(play&&!reduced&&visible)detail.play().catch(()=>{});
}
const fmt=n=>Number.isFinite(n)?Number(n.toPrecision(4)).toLocaleString('en-US',{maximumSignificantDigits:4}):'—';
const mass=n=>n<1?`${fmt(n*1000)} g`:`${fmt(n)} kg`;
const estimate=(value,origin,unit='')=>`${fmt(value)}${unit?' '+unit:''}${origin&&origin!=='source'?'<span class="physics-estimate" title="Estimated parameter"> est.</span>':''}`;
const table=(caption,heads,rows)=>`<div class="scene-joint-scroll" tabindex="0" role="region" aria-label="${caption}"><table><caption>${caption}</caption><thead><tr>${heads.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
async function renderProperties(){
 if(!selected)return;const id=selected.id,v=++version,box=$('#scene-object-properties');
 box.setAttribute('aria-labelledby',`scene-tab-${property}`);box.setAttribute('aria-busy','true');box.innerHTML='<p class="note">Loading physical attributes…</p>';
 try{
  if(!cache.has(id)){const r=await fetch(url(`data/scene-physics/${id}.json`));if(!r.ok)throw Error('Unavailable');cache.set(id,await r.json());}
  if(v!==version)return;const a=cache.get(id),estimated=a.parts.some(p=>p.massOrigin!=='source');
  $('#scene-object-mass').textContent=(estimated?'≈ ':'')+fmt(a.totalMassKg<1?a.totalMassKg*1000:a.totalMassKg);$('#scene-mass-unit').textContent=a.totalMassKg<1?'g':'kg';
  $('#scene-object-summary').textContent=`${a.parts.length} parts · ${a.joints.length} movable joints · ${a.instanceCount} instance`;
  let content,note;
  if(property==='materials'){
   content=table('Part-level mass and materials',['Part','Mass','Materials'],a.parts.map(p=>`<tr><th scope="row">${esc(p.name)}</th><td>${mass(p.massKg)}${p.massOrigin!=='source'?'<small class="physics-estimate">Estimated</small>':''}</td><td>${p.materials.map(m=>esc(m.replaceAll('_',' '))).join(' · ')||'Unspecified'}</td></tr>`));
   note='Total mass is for one instance. “Estimated” values are Qwen3.8-Max annotations; other masses come from matched source parts.';
  }else if(property==='joints'){
   content=table('Articulation and joint limits',['Joint','Motion','Range'],a.joints.map(j=>`<tr><th scope="row">${esc(j.name.replaceAll('_',' '))}</th><td>${esc(j.type)}</td><td>${j.type==='continuous'?'Free rotation':j.lower!=null&&j.upper!=null?`${fmt(j.lower*(j.type==='prismatic'?100:180/Math.PI))} → ${fmt(j.upper*(j.type==='prismatic'?100:180/Math.PI))} ${j.type==='prismatic'?'cm':'°'}`:'Unspecified'}</td></tr>`));
   note='Limits from the native scene asset. Rotation in degrees; travel in centimeters. Continuous joints rotate freely.';
  }else if(property==='dynamics'){
   content=table('Joint effort, velocity, damping and friction',['Joint','Effort / speed','Dynamics'],a.joints.map(j=>{const slide=j.type==='prismatic';return `<tr><th scope="row">${esc(j.name.replaceAll('_',' '))}</th><td>${estimate(j.effort,j.origins.effort,slide?'N':'N·m')}<small>Speed: ${estimate(j.velocity,j.origins.velocity,slide?'m/s':'rad/s')}</small></td><td>Damping: ${estimate(j.damping,j.origins.damping,slide?'N·s/m':'N·m·s/rad')}<small>Friction: ${estimate(j.friction,j.origins.friction,slide?'N':'N·m')}</small></td></tr>`;}));
   note='Source joint parameters are retained. “est.” marks missing values annotated with Qwen3.8-Max (medium).';
  }else{
   content=table('Center of mass (m) and inertia (kg·m²)',['Part','Center of mass','Inertia tensor'],a.parts.map(p=>`<tr><th scope="row">${esc(p.name)}<small>${p.inertiaOrigin==='source'?'Source frame':'Estimated'}</small></th><td>${['x','y','z'].map((k,i)=>`<div>${k}: ${fmt(p.centerOfMass[i])}</div>`).join('')}<small>${p.inertiaOrigin==='source'?'Link-local COM':'Scene-space COM'}</small></td><td>${['ixx','iyy','izz','ixy','ixz','iyz'].map(k=>`<div>${k}: ${fmt(p.inertia[k])}</div>`).join('')}${p.inertiaOrigin==='source'?`<small>RPY: ${p.inertialRotation.map(fmt).join(', ')} rad</small>`:''}</td></tr>`));
   note='Source tensors use the source inertial frame. Missing tensors use Qwen-estimated mass distributions: a diagonal approximation aligned to scene axes, about the estimated center of mass.';
  }
  box.innerHTML=content+`<p class="scene-physics-note">${note}</p>`;
  if(property==='materials'){
   const more=document.createElement('details');more.className='scene-material-details';more.innerHTML='<summary>Material physical properties</summary><div class="scene-material-extra"></div>';box.append(more);
   more.addEventListener('toggle',async()=>{
    if(!more.open||more.dataset.loaded)return;const extra=more.querySelector('.scene-material-extra');extra.textContent='Loading material properties…';
    try{const r=await fetch(url(`data/physics/${id}.json`));if(!r.ok)throw Error('Material data');const {materials}=await r.json();if(v!==version)return;
     extra.innerHTML=`<label class="sr-only" for="scene-material">Material group</label><select id="scene-material">${materials.map((m,i)=>`<option value="${i}">${esc(m.material)}</option>`).join('')}</select><div id="scene-physical-values" class="physics-grid"></div>`;
     const show=i=>{const p=materials[i].values;extra.querySelector('.physics-grid').innerHTML=[['Density',fmt(p.density_kg_m3)+' kg/m³'],['Young’s modulus',fmt(p.youngs_modulus_pa/1e9)+' GPa'],['Poisson’s ratio',fmt(p.poissons_ratio)],['Static friction',fmt(p.static_friction_coefficient)],['Dynamic friction',fmt(p.dynamic_friction_coefficient)],['Restitution',fmt(p.restitution_coefficient)]].map(([k,x])=>`<div><small>${k}</small>${x}</div>`).join('');};extra.querySelector('select').addEventListener('change',e=>show(Number(e.target.value)));show(0);more.dataset.loaded='true';
    }catch{extra.textContent='Material properties could not load. Close and reopen to retry.';}
   });
  }
 }catch{if(v===version)box.innerHTML='<p>Properties could not load. Select this object to retry.</p>';}
 finally{if(v===version)box.setAttribute('aria-busy','false');}
}
document.querySelectorAll('[data-scene-property]').forEach(b=>{b.id=`scene-tab-${b.dataset.sceneProperty}`;b.setAttribute('aria-controls','scene-object-properties');b.addEventListener('click',()=>{property=b.dataset.sceneProperty;document.querySelectorAll('[data-scene-property]').forEach(x=>{x.setAttribute('aria-selected',String(x===b));x.tabIndex=x===b?0:-1;});renderProperties();});});
$('#scene-replay').addEventListener('click',()=>{detail.currentTime=0;detail.play().catch(()=>{});});
new IntersectionObserver(([e])=>{visible=e.isIntersecting;if(!visible)detail.pause();},{threshold:.1}).observe(detail);
document.addEventListener('visibilitychange',()=>{if(document.hidden){detail.pause();overview.pause();}});
Promise.all([fetch(url('data/scenes.json')).then(r=>{if(!r.ok)throw Error('Scene data');return r.json();}),fetch(url('data/catalog.json')).then(r=>r.json())]).then(([d,c])=>{data=d;catalog=c;data.forEach(s=>{const label=document.querySelector(`.scene-picker [data-scene="${s.id}"] small`);if(label)label.textContent=`${s.objects.length} selectable`;});setScene(scene);document.querySelectorAll('.scene-picker [data-scene]').forEach(b=>b.addEventListener('click',()=>setScene(b.dataset.scene)));}).catch(()=>{$('#scene-object-choices').textContent='Scene exploration could not load. Please reload to try again.';});
