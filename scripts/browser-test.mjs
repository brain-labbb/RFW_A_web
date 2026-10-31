import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {readFile,access,mkdir,writeFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url), report={checks:[],errors:[]};
const check=(name,condition)=>{assert.ok(condition,name);report.checks.push(name);console.log('PASS',name);};
const resources=JSON.parse(await readFile(new URL('public/data/resources.json',root),'utf8'));check('Paper link is published; Code and Dataset remain pending',/^https:\/\//.test(resources.paper)&&resources.code===null&&resources.dataset===null);
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:1050}});const errors=[];
page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
await page.goto(process.env.TEST_URL||'http://127.0.0.1:4173/',{waitUntil:'networkidle'});await page.waitForFunction(()=>window.rfwExplorer?.manifest,{timeout:60000});
check('Only Code and Dataset hero release buttons are pending',await page.locator('.resource-links button:disabled').count()===2);
check('Hero Paper link points to the published URL',await page.locator('.resource-links a').first().getAttribute('href')===resources.paper);
check('No local paper PDF is linked',await page.locator('a[href$=".pdf"]').count()===0);
for(const s of ['indoor','outdoor','space','laboratory']){
 await page.locator(`[data-scene="${s}"]`).click();await page.waitForFunction(()=>document.querySelector('#scene-map-image').complete&&document.querySelector('#scene-map-image').naturalWidth>0,{timeout:20000});
 check(`${s} scene switch`,await page.locator(`[data-scene="${s}"]`).getAttribute('aria-selected')==='true');
}
await page.locator('#sample-count').fill('1000');check('Cost calculator uses the paper formula',await page.locator('#our-cost').textContent()==='$0.011');await page.locator('#sample-count').fill('200');
for(const e of ['component','count','material','size']){
 await page.locator('#editing').scrollIntoViewIfNeeded();
 await page.waitForFunction(()=>window.__editingReady,null,{timeout:60000});
 await page.locator(`#edit3d-kinds [data-k="${e}"]`).click();
 await page.waitForFunction(()=>document.querySelectorAll('#edit3d-values button').length>0);
 const buttons=await page.locator('#edit3d-values button').count();
 await page.locator('#edit3d-values button').nth(buttons-1).click();
 await page.waitForFunction(()=>window.rfwEditing?.newView?.model,null,{timeout:60000});
 check(`${e} editing variant renders`,await page.locator('#edit3d-values button').last().getAttribute('aria-pressed')==='true'&&await page.locator('#edit3d-new canvas').isVisible());
}
await page.locator('#edit3d-kinds [data-k="count"]').click();
await page.locator('#edit3d-values button').last().click();
check('Variant selection updates the config readout',(await page.locator('#edit3d-code').textContent()).includes('door_count'));
for(const o of [1,4]){
 await page.locator(`#edit3d-objects button`).nth(o).click();await page.waitForFunction(()=>window.rfwEditing?.newView?.model,null,{timeout:60000});
 check(`Object ${o} switches with variants`,await page.locator('#edit3d-values button').count()>0);
}
await page.locator('#edit3d-objects button').nth(0).click();
await page.locator('[data-result="validity"]').click();check('Quality table has all eight datasets',await page.locator('#results-table tbody tr').count()===8);
await page.locator('[data-result="transfer"]').click();await page.locator('#split-select').selectOption('in');check('Articulation-estimation split changes',await page.locator('#results-table').textContent().then(t=>t.includes('0.78873')));
await page.locator('[data-result="scale"]').click();await page.locator('[data-sort="1"]').click();check('Result table sorts numerically',await page.locator('#results-table tbody tr').first().textContent().then(t=>t.includes('RFW-A')));
await page.locator('#sim2real').scrollIntoViewIfNeeded();await page.waitForFunction(()=>window.__roboticsReady);
for(const task of ['round_cabinet','folding_chair','double_door','toaster','folding_ruler']){
 await page.locator(`[data-task="${task}"]`).click();
 check(`${task} shows five simulation clips and one real-world clip`,await page.locator('#robotics-grid video').count()===6&&await page.locator('#robotics-grid .robotics-real').count()===1);
}
await page.locator('#robotics-replay').click();await page.waitForFunction(()=>[...document.querySelectorAll('#robotics-grid video')].some(v=>v.currentTime>0),{timeout:20000});check('Robotics recordings decode and play',true);await page.locator('#robotics-play').click();
await page.locator('.film-open').click();check('Film opens in a dialog',await page.locator('#film-dialog').isVisible());await page.keyboard.press('Escape');check('Closing film pauses playback',await page.locator('#film-dialog video').evaluate(v=>v.paused));
await page.locator('[data-scene="indoor"]').click();await page.locator('#scene-play').click();await page.evaluate(()=>document.querySelector('#scene-video').pause());await page.locator('#edit3d-kinds [data-k="component"]').click();
await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'/tmp/rfw-web/desktop-final.png',fullPage:true});
check('Desktop has no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
const mobile=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:1});
mobile.on('pageerror',e=>errors.push(e.message));await mobile.goto(process.env.TEST_URL||'http://127.0.0.1:4173/',{waitUntil:'networkidle'});await mobile.waitForFunction(()=>window.rfwExplorer?.manifest,{timeout:60000});
check('Mobile has no horizontal overflow',await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await mobile.locator('.menu-toggle').click();check('Mobile navigation opens',await mobile.locator('.header nav').isVisible());await mobile.locator('.header nav a[href="#editing"]').click();check('Mobile navigation closes after selection',await mobile.locator('.menu-toggle').getAttribute('aria-expanded')==='false');
await mobile.evaluate(()=>window.scrollTo(0,0));await mobile.screenshot({path:'/tmp/rfw-web/mobile-final.png',fullPage:true});
await mobile.setViewportSize({width:320,height:800});check('320px layout has no horizontal overflow',await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
check('No browser errors or failed network requests',errors.length===0);
report.errors=errors;await writeFile('/tmp/rfw-web/browser-test-report.json',JSON.stringify(report,null,2));await browser.close();console.log('All browser checks passed.');
