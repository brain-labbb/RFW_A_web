import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
const base=process.env.TEST_URL||'http://127.0.0.1:4176/';await mkdir('/tmp/rfw-hero',{recursive:true});
const b=await chromium.launch({headless:true,args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const p=await b.newPage({viewport:{width:1440,height:1000}});const errors=[],checks=[];p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});const ok=(n,v)=>{assert.ok(v,n);checks.push(n);console.log('PASS',n);};
await p.goto(base,{waitUntil:'networkidle'});await p.waitForSelector('.hero-author-list>span');
ok('All 22 authors remain visible',await p.locator('.hero-author-list>span').count()===22);
ok('Benchmark is absent from navigation and hero actions',await p.locator('.header nav a[href="#benchmark"],.hero-actions a[href="#benchmark"]').count()===0);
ok('Six release buttons remain pending',await p.locator('.resource-links button:disabled').count()===6);
ok('Video masthead spans the viewport',await p.locator('.project-hero').evaluate(e=>e.clientWidth===innerWidth&&e.clientHeight>=innerHeight-56));
for(const id of ['indoor','outdoor','space','laboratory']){
 await p.locator(`[data-hero-scene="${id}"]`).click();await p.waitForFunction(()=>{const v=document.querySelector('#hero-video');return v.readyState>=2&&v.currentTime>0;},{},{timeout:30000});ok(`${id} background plays muted`,await p.locator('#hero-video').evaluate(v=>v.muted&&!v.paused));
}
await p.locator('#hero-play').click();await p.waitForFunction(()=>document.querySelector('#hero-video').paused&&document.querySelector('#hero-play').textContent==='Play video');ok('Background pause control works',await p.locator('#hero-play').textContent()==='Play video');
await p.locator('#hero-view').click();ok('Watch scene hides and removes metadata from keyboard navigation',await p.locator('#hero-paper-info').evaluate(e=>e.inert&&e.getAttribute('aria-hidden')==='true'));await p.screenshot({path:'/tmp/rfw-hero/watch-scene.png'});
await p.keyboard.press('Escape');ok('Escape restores paper details',await p.locator('#hero-paper-info').getAttribute('aria-hidden')==='false');
await p.locator('#hero-view').click();await p.locator('[data-show-paper]').click();ok('Paper navigation restores metadata',await p.locator('#hero-paper-info').evaluate(e=>!e.inert));
await p.locator('[data-hero-scene="space"]').click();await p.locator('#hero-explore').click();ok('Explore this scene selects the matching scene',await p.locator('.scene-picker [data-scene="space"]').getAttribute('aria-selected')==='true');
await p.locator('[data-show-paper]').click();await p.locator('.hero-film').click();await p.waitForFunction(()=>{const v=document.querySelector('#film-dialog video');return v.readyState>=2&&!v.paused;},{},{timeout:30000});
ok('Supplied 2:24 film plays with sound enabled',await p.locator('#film-dialog video').evaluate(v=>!v.muted&&Math.abs(v.duration-144.178571)<.2));
ok('Opening the full film pauses other videos',await p.evaluate(()=>[...document.querySelectorAll('video')].filter(v=>!v.closest('#film-dialog')).every(v=>v.paused)));
await p.keyboard.press('Escape');ok('Closing the film stops its playback',await p.locator('#film-dialog video').evaluate(v=>v.paused));
await p.locator('[data-hero-scene="indoor"]').click();await p.locator('#hero-video').evaluate(v=>{v.pause();v.currentTime=0;});await p.screenshot({path:'/tmp/rfw-hero/desktop-final.png'});
await p.setViewportSize({width:390,height:844});await p.locator('.project-hero').screenshot({path:'/tmp/rfw-hero/mobile-final.png'});ok('Mobile layout fits',await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.setViewportSize({width:320,height:800});ok('320px layout fits',await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
const reduced=await b.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});await reduced.goto(base,{waitUntil:'networkidle'});ok('Reduced-motion visitors get readable metadata and a paused background',await reduced.locator('#hero-video').evaluate(v=>v.paused)&&await reduced.locator('#hero-paper-info').evaluate(e=>!e.inert));
ok('No browser errors or missing resources',errors.length===0);await writeFile('/tmp/rfw-hero/validation.json',JSON.stringify({checks,errors},null,2));await b.close();
