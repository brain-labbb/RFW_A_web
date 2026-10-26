import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
const base=process.env.TEST_URL||'http://127.0.0.1:4175/';const scenes=JSON.parse(await readFile(new URL('../public/data/scenes.json',import.meta.url)));
await mkdir('/tmp/rfw-scenes',{recursive:true});const b=await chromium.launch({headless:true,args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const p=await b.newPage({viewport:{width:1440,height:1050}});const errors=[],checks=[];p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});const ok=(name,v)=>{assert.ok(v,name);checks.push(name);console.log('PASS',name);};
await p.goto(base,{waitUntil:'networkidle'});await p.waitForSelector('.scene-pin');
for(const s of scenes){
 await p.locator(`.scene-picker [data-scene="${s.id}"]`).click();await p.locator('#worlds').scrollIntoViewIfNeeded();
 ok(`${s.id}: three projected scene hotspots`,await p.locator('.scene-pin').count()===3);
 for(const a of s.objects){
  ok(`${a.name}: projected polygon stays inside map`,a.polygon.length>=3&&a.polygon.every(q=>q.every(v=>v>=0&&v<=1)));
  await p.locator(`#scene-object-choices [data-scene-object="${a.id}"]`).click();await p.waitForFunction(id=>document.querySelector('.scene-inspector').dataset.selected===id,a.id);
  await p.locator('#scene-detail-video').evaluate(v=>{v.play().catch(()=>{});});await p.waitForFunction(()=>{const v=document.querySelector('#scene-detail-video');return v.readyState>=2&&v.currentTime>.05;},{},{timeout:30000});
  ok(`${a.name}: new camera clip decodes and plays`,await p.locator('#scene-detail-video').evaluate(v=>v.videoWidth===960&&Math.abs(v.duration-5)<.15));
  await p.locator('[data-scene-property="materials"]').click();await p.waitForSelector('#scene-material');ok(`${a.name}: material properties match selection`,await p.locator('#scene-physical-values>div').count()===6);
  await p.locator('[data-scene-property="joints"]').click();ok(`${a.name}: joint records available`,await p.locator('.scene-joint-scroll tbody tr').count()>0);
 }
 await p.locator('[data-scene-property="materials"]').click();await p.waitForSelector('#scene-material');await p.locator('#scene-detail-video').evaluate(v=>v.pause());await p.locator('#worlds').screenshot({path:`/tmp/rfw-scenes/web-${s.id}.png`});
}
await p.locator('#scene-play').click();await p.waitForFunction(()=>!document.querySelector('#scene-video').paused&&document.querySelector('.scene-map').classList.contains('is-playing'));ok('Overview playback hides static hotspots',await p.locator('.scene-map').evaluate(e=>e.classList.contains('is-playing')));await p.locator('#scene-play').click();await p.waitForFunction(()=>!document.querySelector('.scene-map').classList.contains('is-playing'));ok('Return to map restores selectable objects',await p.locator('.scene-map').evaluate(e=>!e.classList.contains('is-playing')));
await p.setViewportSize({width:390,height:844});await p.locator('.scene-picker [data-scene="space"]').click();await p.locator('#scene-object-choices button').nth(1).click();await p.locator('#scene-detail-video').evaluate(v=>v.pause());ok('Mobile page fits viewport',await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.locator('#worlds').screenshot({path:'/tmp/rfw-scenes/web-mobile.png'});
await p.setViewportSize({width:320,height:800});ok('320px page fits viewport',await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
const target=scenes[3].objects[0];await p.goto(new URL(`demo.html?asset=${target.id}`,base).href,{waitUntil:'networkidle'});await p.waitForFunction(()=>document.querySelector('#demo-loading').hidden,{},{timeout:60000});ok('Scene object link opens its native 3D asset',await p.locator(`.demo-item[data-id="${target.id}"]`).evaluate(e=>e.classList.contains('active')));
ok('No page errors or missing resources',errors.length===0);await writeFile('/tmp/rfw-scenes/browser-validation.json',JSON.stringify({checks,errors},null,2));await b.close();
