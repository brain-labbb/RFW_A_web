import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {readFile,access,mkdir,writeFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url), report={checks:[],errors:[]};
const check=(name,condition)=>{assert.ok(condition,name);report.checks.push(name);console.log('PASS',name);};
const catalog=JSON.parse(await readFile(new URL('public/data/catalog.json',root),'utf8'));
check('84 scene instances in catalog',catalog.length===84);
let groups=0;
for(const a of catalog){
 await access(new URL('public/'+a.model,root));await access(new URL('public/'+a.thumbnail,root));
 const p=JSON.parse(await readFile(new URL('public/data/physics/'+a.id+'.json',root),'utf8'));
 assert.ok(p.materials.length>0);groups+=p.materials.length;
 for(const m of p.materials){const v=m.values;assert.ok(Object.values(v).every(Number.isFinite));assert.ok(v.density_kg_m3>0&&v.youngs_modulus_pa>0);assert.ok(v.poissons_ratio> -1&&v.poissons_ratio<.5);assert.ok(v.static_friction_coefficient>=v.dynamic_friction_coefficient&&v.dynamic_friction_coefficient>=0);assert.ok(v.restitution_coefficient>=0&&v.restitution_coefficient<=1);}
}
check('All 84 GLBs, previews, and physical-property files exist',true);check(`${groups} material property groups pass range and completeness checks`,groups>0);
const resources=JSON.parse(await readFile(new URL('public/data/resources.json',root),'utf8'));check('Paper, Code, Dataset remain unpublished',Object.values(resources).every(x=>x===null));
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:1050}});const errors=[];
page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
await page.goto(process.env.TEST_URL||'http://127.0.0.1:4173/',{waitUntil:'networkidle'});await page.waitForFunction(()=>window.__viewerReady,{timeout:60000});
check('All six release buttons are pending',await page.locator('.resource-links button:disabled').count()===6);
check('No local paper PDF is linked',await page.locator('a[href$=".pdf"]').count()===0);
for(const s of ['indoor','outdoor','space','laboratory']){
 await page.locator(`[data-scene="${s}"]`).click();await page.waitForFunction(()=>document.querySelector('#scene-video').readyState>=1,{timeout:20000});
 check(`${s} scene and asset filter switch`,await page.locator(`[data-scene="${s}"]`).getAttribute('aria-selected')==='true'&&await page.locator(`[data-filter="${s}"]`).getAttribute('aria-pressed')==='true');
}
await page.locator('[data-filter="all"]').click();await page.locator('#asset-search').fill('astronaut');check('Asset search finds the helmet',await page.locator('.asset-card').count()===1);await page.locator('.asset-card').click();await page.waitForFunction(()=>window.__viewerReady.includes('helmet'),{timeout:60000});
await page.locator('#asset-search').fill('nothing-matches-123');check('Empty search has a useful state',await page.locator('.empty-results').isVisible());await page.locator('#asset-search').fill('');
await page.evaluate(id=>window.rfw.selectAsset(id),catalog[0].id);await page.locator('#explore').scrollIntoViewIfNeeded();
const moved=await page.evaluate(()=>{const v=window.rfw.viewer;const state=()=>{v.model.updateMatrixWorld(true);let a=[];v.model.traverse(o=>a.push(...o.matrixWorld.elements));return JSON.stringify(a);};v.seek(0);const before=state();v.seek(.5);return before!==state();});
check('Scrubbing changes actual model transforms',moved);
await page.locator('#motion-play').click();check('Motion play/pause works',await page.locator('#motion-play').getAttribute('aria-label')==='Pause asset motion');await page.locator('#motion-play').click();
await page.locator('[data-info="materials"]').click();await page.waitForSelector('#material-select');check('Six physical properties render',await page.locator('.physics-grid>div').count()===6);await page.selectOption('#material-select','1');
await page.locator('#sample-count').fill('1000');check('Cost calculator uses the paper formula',await page.locator('#our-cost').textContent()==='$0.011');await page.locator('#sample-count').fill('200');
for(const e of ['component','count','material','size']){
 await page.locator(`[data-edit="${e}"]`).click();await page.locator('[data-variant="3"]').click();await page.waitForFunction(()=>document.querySelector('#edit-after').complete&&document.querySelector('#edit-after').naturalWidth>0);check(`${e} editing variant renders`,await page.locator('[data-variant="3"]').getAttribute('aria-pressed')==='true');
}
await page.locator('[data-result="validity"]').click();check('Quality table has all eight datasets',await page.locator('#results-table tbody tr').count()===8);
await page.locator('[data-result="transfer"]').click();await page.locator('#split-select').selectOption('in');check('Articulation-estimation split changes',await page.locator('#results-table').textContent().then(t=>t.includes('0.78873')));
await page.locator('[data-result="scale"]').click();await page.locator('[data-sort="1"]').click();check('Result table sorts numerically',await page.locator('#results-table tbody tr').first().textContent().then(t=>t.includes('RFW-A')));
for(const task of ['round_cabinet','folding_chair','double_door','toaster','folding_ruler']){
 await page.locator(`[data-task="${task}"]`).click();await page.evaluate(()=>{document.querySelector('#sim-video').load();document.querySelector('#real-video').load();});
 check(`${task} has matched simulation and real videos`,await page.locator('#sim-video').getAttribute('src').then(s=>s.includes(task))&&await page.locator('#real-video').getAttribute('src').then(s=>s.includes(task)));
}
await page.locator('#play-pair').click();await page.waitForFunction(()=>document.querySelector('#sim-video').currentTime>0&&document.querySelector('#real-video').currentTime>0,{timeout:20000});check('Paired videos decode and play',true);await page.locator('#play-pair').click();
await page.locator('.film-open').click();check('Film opens in a dialog',await page.locator('#film-dialog').isVisible());await page.keyboard.press('Escape');check('Closing film pauses playback',await page.locator('#film-dialog video').evaluate(v=>v.paused));
await page.locator('[data-scene="indoor"]').click();await page.locator('#scene-play').click();await page.evaluate(()=>document.querySelector('#scene-video').pause());await page.locator('[data-filter="all"]').click();await page.locator('[data-info="structure"]').click();await page.locator('[data-edit="component"]').click();
await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'/tmp/rfw-web/desktop-final.png',fullPage:true});
check('Desktop has no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
const mobile=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:1});
mobile.on('pageerror',e=>errors.push(e.message));await mobile.goto(process.env.TEST_URL||'http://127.0.0.1:4173/',{waitUntil:'networkidle'});await mobile.waitForFunction(()=>window.__viewerReady,{timeout:60000});
check('Mobile has no horizontal overflow',await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await mobile.locator('.menu-toggle').click();check('Mobile navigation opens',await mobile.locator('.header nav').isVisible());await mobile.locator('.header nav a[href="#editing"]').click();check('Mobile navigation closes after selection',await mobile.locator('.menu-toggle').getAttribute('aria-expanded')==='false');
await mobile.evaluate(()=>window.scrollTo(0,0));await mobile.screenshot({path:'/tmp/rfw-web/mobile-final.png',fullPage:true});
await mobile.setViewportSize({width:320,height:800});check('320px layout has no horizontal overflow',await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
check('No browser errors or failed network requests',errors.length===0);
report.errors=errors;await writeFile('/tmp/rfw-web/browser-test-report.json',JSON.stringify(report,null,2));await browser.close();console.log('All browser checks passed.');
