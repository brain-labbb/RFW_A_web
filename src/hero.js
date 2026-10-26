const $=s=>document.querySelector(s),hero=$('.project-hero'),video=$('#hero-video'),info=$('#hero-paper-info'),play=$('#hero-play'),view=$('#hero-view'),film=$('#film-dialog');
const reduced=matchMedia('(prefers-reduced-motion: reduce)'),base=import.meta.env.BASE_URL;
let scene='indoor',watching=false,visible=true,wantsPlay=!reduced.matches&&!navigator.connection?.saveData;
const ext=video.canPlayType('video/mp4; codecs="avc1.42E01E"')?'mp4':'webm';
function playback(){play.textContent=video.paused?'Play video':'Pause video';play.setAttribute('aria-label',video.paused?'Play background scene':'Pause background scene');}
function requestPlay(){if(wantsPlay&&visible&&!document.hidden&&!film.open)video.play().catch(playback);}
function showPaper(show){watching=!show;hero.classList.toggle('is-watching',watching);info.inert=watching;info.setAttribute('aria-hidden',String(watching));view.setAttribute('aria-expanded',String(show));view.textContent=show?'Watch scene':'Show paper details';}
function chooseScene(id){scene=id;video.pause();video.poster=base+`media/scenes/${id}.webp`;video.src=base+`media/${id}.${ext}`;video.load();video.setAttribute('aria-label',`RFW-A ${id} scene`);document.querySelectorAll('[data-hero-scene]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.heroScene===id)));$('#hero-scene-caption').textContent=`${id[0].toUpperCase()+id.slice(1)} · Articulated assets generated with RFW-A`;requestPlay();}
document.querySelectorAll('[data-hero-scene]').forEach(b=>b.addEventListener('click',()=>chooseScene(b.dataset.heroScene)));
video.addEventListener('play',playback);video.addEventListener('pause',playback);video.addEventListener('loadeddata',requestPlay);
play.addEventListener('click',()=>{wantsPlay=video.paused;if(wantsPlay)requestPlay();else video.pause();});
view.addEventListener('click',()=>showPaper(watching));
$('#hero-explore').addEventListener('click',()=>document.querySelector(`.scene-picker [data-scene="${scene}"]`)?.click());
document.querySelector('[data-show-paper]').addEventListener('click',e=>{e.preventDefault();showPaper(true);hero.scrollIntoView({behavior:'instant'});$('#paper-title').focus({preventScroll:true});});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&watching)showPaper(true);});
new IntersectionObserver(([e])=>{visible=e.isIntersecting;if(visible)requestPlay();else video.pause();},{threshold:.08}).observe(hero);
document.addEventListener('visibilitychange',()=>document.hidden?video.pause():requestPlay());
// The narrated film owns playback while its dialog is open.
new MutationObserver(()=>{if(film.open){document.querySelectorAll('video').forEach(v=>{if(!film.contains(v))v.pause();});}else requestPlay();}).observe(film,{attributes:true,attributeFilter:['open']});
reduced.addEventListener('change',()=>{if(reduced.matches){wantsPlay=false;video.pause();}});
if(!wantsPlay){video.autoplay=false;video.pause();}else if(ext==='webm'){video.src=base+'media/indoor.webm';}
playback();requestPlay();
