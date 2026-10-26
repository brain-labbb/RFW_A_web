import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
await mkdir('/tmp/rfw-dataset',{recursive:true});
const base=process.env.TEST_URL||'http://127.0.0.1:4180/';
const data=JSON.parse(await readFile(new URL('../public/data/dataset.json',import.meta.url)));
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[],requests=[];const checks=[];
const ok=(name,value)=>{assert.ok(value,name);checks.push(name);console.log('PASS',name);};
page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});page.on('request',r=>requests.push(r.url()));
await page.goto(base,{waitUntil:'networkidle'});await page.waitForSelector('#dataset-gallery .dataset-card');await page.locator('#dataset').scrollIntoViewIfNeeded();await page.waitForTimeout(500);
ok('12 representative categories render',await page.locator('#dataset-gallery .dataset-card').count()===12);
ok('Dataset 3D models are not fetched before selection',!requests.some(u=>u.includes('/models/dataset/')));
for(const domain of ['Home','Space','Industry','Healthcare']){await page.selectOption('#dataset-domain',domain);const expected=data.gallery.map(id=>data.assets.find(a=>a.id===id)).filter(a=>a.domain===domain).length;ok(`${domain} filters representative categories`,await page.locator('#dataset-gallery .dataset-card').count()===expected);}
await page.selectOption('#dataset-domain','all');
for(const family of data.families){await page.locator(`[data-family="${family.id}"]`).click();ok(`${family.name}: same generator version, four distinct seeds`,new Set(family.samples.map(id=>data.assets.find(a=>a.id===id).templateHash)).size===1&&await page.locator('#family-grid .dataset-card').count()===4);}
await page.locator('[data-family="drawer_cabinet_with_sliding_drawers"]').click();await page.locator('.family-showcase').screenshot({path:'/tmp/rfw-dataset/family-desktop.png'});
// Open every selected model and verify browser rig coverage and a responsive joint slider.
for(const asset of data.assets){
 const card=page.locator(`[data-sample="${asset.id}"]`).first();
 if(!await card.count())await page.locator(`[data-family="${asset.category}"]`).click();
 await page.locator(`[data-sample="${asset.id}"]`).first().click();
 await page.waitForFunction(id=>document.querySelector('#dataset-dialog').dataset.loaded===id,asset.id,{timeout:60000});
 const count=await page.locator('#dataset-joint option').count();ok(`${asset.id}: model and ${count} controllable joints`,count===asset.joints.length);
 if(count){const before=await page.locator('#dataset-viewer canvas').screenshot();await page.locator('#dataset-joint-value').fill('700');await page.waitForTimeout(160);const after=await page.locator('#dataset-viewer canvas').screenshot();ok(`${asset.id}: changing joint position changes rendering`,!before.equals(after));}
 await page.locator('#dataset-parts').click();ok(`${asset.id}: part view toggles`,await page.locator('#dataset-parts').getAttribute('aria-pressed')==='true');
 if(asset.id==='drawer_cabinet_with_sliding_drawers__0016')await page.locator('#dataset-dialog').screenshot({path:'/tmp/rfw-dataset/inspector-desktop.png'});
 await page.keyboard.press('Escape');
}
// A fresh URL can reopen a particular dataset sample.
const deep=new URL(base);deep.searchParams.set('sample',data.assets[0].id);await page.goto(deep.href,{waitUntil:'networkidle'});await page.waitForFunction(()=>document.querySelector('#dataset-dialog').dataset.loaded,{timeout:60000});ok('Shareable sample URL opens the right model',await page.locator('#dataset-dialog').getAttribute('data-loaded')===data.assets[0].id);await page.keyboard.press('Escape');
await page.setViewportSize({width:390,height:844});await page.locator('#dataset').scrollIntoViewIfNeeded();ok('Mobile document fits viewport',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.locator('[data-family="drawer_cabinet_with_sliding_drawers"]').click();await page.locator('#family-grid .dataset-card').first().click();await page.waitForFunction(()=>document.querySelector('#dataset-dialog').dataset.loaded?.includes('drawer'),{timeout:60000});ok('Mobile inspector fits viewport',await page.locator('#dataset-dialog').evaluate(e=>e.scrollWidth<=e.clientWidth+1));await page.locator('#dataset-dialog').screenshot({path:'/tmp/rfw-dataset/inspector-mobile.png'});await page.keyboard.press('Escape');await page.locator('#dataset').screenshot({path:'/tmp/rfw-dataset/dataset-mobile.png'});
await page.setViewportSize({width:320,height:800});ok('320px viewport fits without horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
ok('No browser exceptions or missing assets',errors.length===0);
await writeFile('/tmp/rfw-dataset/browser-validation.json',JSON.stringify({checks,errors},null,2));await browser.close();
