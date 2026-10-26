// Curated PV_A_vlm examples. No remote dataset/API access occurs in the browser.
const $=s=>document.querySelector(s),base=import.meta.env.BASE_URL,url=p=>base+p;
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let manifest,byId,viewer,viewerModule,loadVersion=0,selected,rig=[],partMode=false;
const dialog=$('#dataset-dialog');
const seedLabel=a=>'seed '+String(a.seed).padStart(4,'0');
function card(a,family=false){return `<button class="dataset-card" data-sample="${a.id}" aria-label="Inspect ${escape(a.name)}, ${seedLabel(a)}"><img src="${url(a.image)}" alt="${escape(a.name)}, ${seedLabel(a)}" width="640" height="480" loading="lazy"/><span class="dataset-card-title">${family?seedLabel(a):escape(a.name)}<span aria-hidden="true">↗</span></span><span class="dataset-card-meta">${family?escape(a.features.join(' · ')):escape(a.domain)} · ${a.joints.length} joints</span></button>`;}
function bindCards(root){root.querySelectorAll('[data-sample]').forEach(b=>b.addEventListener('click',()=>openAsset(byId.get(b.dataset.sample))));}
function renderGallery(){const domain=$('#dataset-domain').value,assets=manifest.gallery.map(id=>byId.get(id)).filter(a=>domain==='all'||a.domain===domain);$('#dataset-gallery').innerHTML=assets.map(a=>card(a)).join('');bindCards($('#dataset-gallery'));}
function renderFamily(f){
 document.querySelectorAll('[data-family]').forEach(b=>{const on=b.dataset.family===f.id;b.setAttribute('aria-selected',on);b.tabIndex=on?0:-1;});
 $('#family-name').textContent=f.name;$('#family-grid').innerHTML=f.samples.map(id=>card(byId.get(id),true)).join('');$('#family-description').textContent=f.description;$('#family-hash').textContent=f.templateHash;bindCards($('#family-grid'));
}
async function getViewer(){
 if(!viewerModule)viewerModule=import('./viewer.js');
 const {AssetViewer}=await viewerModule;
 if(!viewer)viewer=new AssetViewer($('#dataset-viewer'));
 return viewer;
}
function clearJointUI(){rig=[];$('#dataset-joint').innerHTML='';$('#dataset-joint').disabled=true;$('#dataset-joint-value').disabled=true;$('#dataset-joint-output').textContent='';}
function jointUI(){
 const joint=rig[Number($('#dataset-joint').value)];if(!joint)return;
 $('#dataset-joint-value').value=Math.round((joint.value-joint.lower)/(joint.upper-joint.lower)*1000);
 $('#dataset-joint-output').textContent=joint.value.toFixed(3)+(joint.type==='prismatic'?' m':' rad');
}
function setJoint(fraction){
 const joint=rig[Number($('#dataset-joint').value)];if(!joint)return;
 joint.value=joint.lower+fraction*(joint.upper-joint.lower);const o=joint.object,axis=joint.axis;
 o.position.copy(joint.basePosition);o.quaternion.copy(joint.baseRotation);
 if(joint.type==='prismatic')o.position.add(axis.clone().applyQuaternion(joint.baseRotation).multiplyScalar(joint.value));
 else o.quaternion.multiply(new viewer.THREE.Quaternion().setFromAxisAngle(axis,joint.value));
 viewer.model.updateMatrixWorld(true);jointUI();
}
function configureRig(){
 const T=viewer.THREE;
 viewer.model.traverse(o=>{
  const d=o.userData;if(!d.rfw_joint)return;const type=d.rfw_type;let lower=d.rfw_lower,upper=d.rfw_upper;
  if(type==='continuous'){lower=-Math.PI;upper=Math.PI;}
  if(!['continuous','revolute','prismatic'].includes(type)||!Number.isFinite(lower)||!Number.isFinite(upper)||upper<=lower)return;
  const [x,y,z]=d.rfw_axis; // Blender glTF applies the same Z-up -> Y-up basis change to node transforms.
  rig.push({name:d.rfw_joint,type,lower,upper,value:0,axis:new T.Vector3(x,z,-y).normalize(),object:o,basePosition:o.position.clone(),baseRotation:o.quaternion.clone()});
 });
 $('#dataset-joint').innerHTML=rig.map((j,i)=>`<option value="${i}">${escape(j.name)} · ${j.type}</option>`).join('');
 $('#dataset-joint').disabled=!rig.length;$('#dataset-joint-value').disabled=!rig.length;
 if(rig.length){$('#dataset-joint').value='0';jointUI();}else $('#dataset-joint-output').textContent='No adjustable joint';
}
function colorParts(on){
 if(!viewer?.model)return;partMode=on;let colors=new Map();
 viewer.model.traverse(o=>{if(!o.isMesh)return;const part=o.userData.rfw_part||o.name;
  if(!colors.has(part))colors.set(part,new viewer.THREE.Color().setHSL((colors.size*.61803398875)%1,.48,.53));
  if(!o.userData.originalMaterials){o.userData.originalMaterials=o.material;o.userData.partMaterials=[].concat(o.material).map(m=>{const c=m.clone();c.color.copy(colors.get(part));c.map=null;c.metalness=0;c.roughness=.8;return c;});}
  o.material=on?(Array.isArray(o.userData.originalMaterials)?o.userData.partMaterials:o.userData.partMaterials[0]):o.userData.originalMaterials;
 });
 $('#dataset-parts').setAttribute('aria-pressed',on);$('#dataset-parts').textContent=on?'Show materials':'Show parts';
}
function releasePartMaterials(){if(!viewer?.model)return;colorParts(false);viewer.model.traverse(o=>o.userData.partMaterials?.forEach(m=>m.dispose()));}
async function openAsset(a){
 selected=a;const version=++loadVersion;delete dialog.dataset.loaded;clearJointUI();if(!dialog.open)dialog.showModal();
 $('#dataset-asset-title').textContent=a.name;$('#dataset-asset-tag').textContent=`${a.domain} · ${seedLabel(a)} · RFW-A-400K`;
 $('#dataset-asset-facts').innerHTML=[['Links',a.links],['Movable joints',a.joints.length],['Visual surfaces',a.surfaces],['Material classes',a.materialClasses.length]].map(([k,v])=>`<div><strong>${v}</strong><span>${k}</span></div>`).join('');
 $('#dataset-materials').innerHTML=a.materialClasses.map(c=>`<span>${escape(c.replaceAll('_',' ').replaceAll('.',' / '))}</span>`).join('');
 $('#dataset-sample-record').innerHTML=`<p>Category: ${escape(a.category)}</p><p>Seed: ${a.seed}</p><p>URDF SHA-256</p><code>${a.urdfHash}</code><p>Generator SHA-256</p><code>${a.templateHash}</code>`;
 $('#dataset-loading').hidden=false;$('#dataset-loading').textContent='Loading dataset sample…';$('#dataset-parts').disabled=true;$('#dataset-share').textContent='Copy sample link';
 try{
  const v=await getViewer();if(version!==loadVersion)return;releasePartMaterials();const loaded=await v.load(url(a.model));if(version!==loadVersion||!loaded)return;
  v.resize();configureRig();partMode=false;$('#dataset-parts').textContent='Show parts';$('#dataset-parts').setAttribute('aria-pressed','false');$('#dataset-parts').disabled=false;
  $('#dataset-loading').hidden=true;dialog.dataset.loaded=a.id;
 }catch(e){if(version!==loadVersion)return;$('#dataset-loading').textContent='Could not load this model. Close and select it to retry.';console.error(e);}
}
$('#dataset-close').addEventListener('click',()=>dialog.close());
dialog.addEventListener('close',()=>{++loadVersion;viewer?.setPlaying(false);});
dialog.addEventListener('click',e=>{const r=dialog.getBoundingClientRect();if(e.target===dialog&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))dialog.close();});
$('#dataset-joint').addEventListener('change',jointUI);$('#dataset-joint-value').addEventListener('input',e=>setJoint(Number(e.target.value)/1000));
$('#dataset-reset').addEventListener('click',()=>{for(const j of rig){j.object.position.copy(j.basePosition);j.object.quaternion.copy(j.baseRotation);j.value=0;}viewer?.reset();jointUI();});
$('#dataset-parts').addEventListener('click',()=>colorParts(!partMode));
$('#dataset-share').addEventListener('click',async()=>{const target=new URL(location.href);target.searchParams.set('sample',selected.id);target.hash='dataset';try{await navigator.clipboard.writeText(target.href);$('#dataset-share').textContent='Copied';}catch{$('#dataset-share').textContent='Link selected';const i=document.createElement('input');i.value=target.href;$('#dataset-sample-record').prepend(i);i.select();}});
$('#dataset-domain').addEventListener('change',renderGallery);
fetch(url('data/dataset.json')).then(r=>{if(!r.ok)throw Error('Dataset manifest unavailable');return r.json();}).then(d=>{
 manifest=d;byId=new Map(d.assets.map(a=>[a.id,a]));renderGallery();$('#family-tabs').innerHTML=d.families.map(f=>`<button role="tab" data-family="${f.id}" aria-selected="false">${f.name}</button>`).join('');
 document.querySelectorAll('[data-family]').forEach(b=>b.addEventListener('click',()=>renderFamily(d.families.find(f=>f.id===b.dataset.family))));renderFamily(d.families[1]);
 const deep=new URLSearchParams(location.search).get('sample');if(byId.has(deep))openAsset(byId.get(deep));
}).catch(()=>{$('#dataset-gallery').innerHTML='<p>Dataset examples could not load. Please reload to try again.</p>';});
