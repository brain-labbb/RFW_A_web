import './explorer.js';
import './scenes.js';
import './hero.js';
import './robotics.js';
import './editing.js';
import './style.css';
import {scenes,scaleRows,qualityRows,transferRows} from './data.js';
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
function updateSceneButton(){scenePlay.innerHTML=video.paused?'▶ <span>Watch scene</span>':'↩ <span>Explore objects</span>';scenePlay.setAttribute('aria-label',video.paused?'Play scene video':'Pause scene video');}
video.addEventListener('play',updateSceneButton);video.addEventListener('pause',updateSceneButton);
scenePlay.addEventListener('click',()=>video.paused?video.play().catch(()=>{}):video.pause());
$$('[data-scene]').forEach(b=>b.addEventListener('click',()=>{
 const s=b.dataset.scene,data=scenes[s];selectTab($$('[data-scene]'),b);video.pause();video.poster=url(`media/${s}.webp`);video.src=videoUrl(s);video.load();
 $('#scene-index').textContent=`${data.index} / 04`;$('#scene-title').innerHTML=data.title;$('#scene-subtitle').textContent=data.subtitle;video.setAttribute('aria-label',`${s} articulated scene`);
 updateSceneButton();

}));
const videoObserver=new IntersectionObserver(entries=>entries.forEach(e=>{if(!e.isIntersecting)e.target.pause();}),{threshold:0.05});$$('video').forEach(v=>videoObserver.observe(v));
// Dialogs retain native focus trapping and Escape behavior.
const film=$('#film-dialog');$$('.film-open').forEach(b=>b.addEventListener('click',()=>{film.showModal();film.querySelector('video').play().catch(()=>{});}));film.addEventListener('close',()=>film.querySelector('video').pause());film.addEventListener('cancel',()=>film.querySelector('video').pause());
$$('dialog').forEach(d=>{d.querySelector('.dialog-close').addEventListener('click',()=>d.close());d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}});});
$$('[data-lightbox]').forEach(b=>b.addEventListener('click',()=>{const d=$('#figure-dialog');d.querySelector('img').src=url(b.dataset.lightboxMobile&&matchMedia('(max-width: 760px)').matches?b.dataset.lightboxMobile:b.dataset.lightbox);d.querySelector('img').alt=b.dataset.caption;d.showModal();}));

$('#sample-count').addEventListener('input',e=>{const n=Number(e.target.value),cost=10.62/n;$('#sample-output').textContent=n.toLocaleString();$('#our-cost').textContent='$'+cost.toFixed(cost<1?3:2);$('#our-cost-bar').style.width=Math.min(100,cost/Math.max(1.237,cost)*100)+'%';$('.cost-row:not(.ours) .cost-track i').style.width=(1.237/Math.max(1.237,cost)*100)+'%';});
$('#sample-count').dispatchEvent(new Event('input'));
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
fetch(url('data/paper.json')).then(r=>r.json()).then(p=>{
 const supers=s=>s.replaceAll('\\dagger','†').replaceAll('\\ddagger','‡');
 $('#author-details').innerHTML=`<div class="hero-author-list">${p.authors.map(([n,a])=>`<span>${esc(a)}<sup>${esc(supers(n))}</sup></span>`).join('')}</div><div class="hero-affiliations">${p.affiliations.map(([n,a])=>`<span><sup>${n}</sup> ${esc(a)}</span>`).join('')}</div><p class="hero-author-notes">* Equal contribution &nbsp; · &nbsp; † Project leader &nbsp; · &nbsp; ‡ Corresponding authors</p>`;$('#hero-abstract-text').textContent=p.abstract;
}).catch(()=>{});
fetch(url('data/resources.json')).then(r=>r.json()).then(resources=>{for(const [key,href]of Object.entries(resources)){if(!href||!/^https:\/\//.test(href))continue;$$('.resource-links button').filter(b=>b.textContent.toLowerCase().startsWith(key)).forEach(b=>{const a=document.createElement('a');a.href=href;a.target='_blank';a.rel='noopener';a.textContent=key[0].toUpperCase()+key.slice(1)+' ↗';b.replaceWith(a);});}}).catch(()=>{});

const citationButton=document.querySelector('#copy-citation');if(citationButton){citationButton.addEventListener('click',async()=>{const text=document.querySelector('#citation-text').textContent;try{await navigator.clipboard.writeText(text);citationButton.textContent='Copied';setTimeout(()=>citationButton.textContent='Copy BibTeX',1400);}catch{citationButton.textContent='Select to copy';}});}
