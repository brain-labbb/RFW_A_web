import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {readFile, writeFile, mkdir} from 'node:fs/promises';

const base=process.env.TEST_URL||'http://127.0.0.1:4175/';
const manifest=JSON.parse(await readFile(new URL('../public/data/explorer.json',import.meta.url)));
await mkdir('/tmp/rfw-explorer',{recursive:true});
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const errors=[],requests=[],checks=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
page.on('request',r=>requests.push(r.url()));
const ok=(name,value)=>{assert.ok(value,name);checks.push(name);console.log('PASS',name);};
await page.goto(base,{waitUntil:'networkidle'});
await page.waitForSelector('[data-category]');
ok('One combined explorer replaces the two old sections',await page.locator('#dataset').count()===1&&await page.locator('#explore,#dataset-dialog').count()===0);
ok('Only 2D previews load before an asset is selected',!requests.some(r=>r.includes('/models/'))&&!requests.some(r=>r.endsWith('.wasm')));
ok('Explore this scene is retained; the two hero buttons are removed',await page.locator('#hero-explore').getAttribute('href')==='#worlds'&&await page.locator('.hero-actions .hero-link').count()===0);
ok('Scene 3D links have been retired',await page.locator('#scene-object-3d,#scene-browse').count()===0);
await page.locator('#gx-more').click();
ok('All 31 new categories are available',await page.locator('[data-category]').count()===31);
ok('The entire blinds category is withdrawn',manifest.assets.length===186&&!manifest.assets.some(a=>a.category==='Curtain_blind')&&!manifest.families.some(f=>f.id==='Curtain_blind')&&await page.locator('[data-category="Curtain_blind"]').count()===0);
await page.locator('#gx-search').fill('headphones');
ok('Category search finds headphones',await page.locator('[data-category]').count()===1);
await page.locator('#gx-search').fill('no category matches');
ok('Search has an empty state',await page.locator('.gx-empty').isVisible());
await page.locator('#gx-search').fill('');
for(const domain of ['Home','Outdoor','Electronics','Tools','Everyday']){
  await page.selectOption('#gx-domain',domain);
  ok(`${domain} category filter`,await page.locator('[data-category]').count()===manifest.families.filter(f=>f.domain===domain).length);
}
await page.selectOption('#gx-domain','all');
await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,document.querySelector('#dataset').offsetTop-70);});
await page.screenshot({path:'/tmp/rfw-explorer/explorer-desktop.png'});

for(const family of manifest.families){
  await page.evaluate(id=>window.rfwExplorer.selectFamily(id),family.id);
  ok(`${family.name}: ${family.samples.length} previews and a source image`,await page.locator('[data-seed]').count()===family.samples.length&&await page.locator('#gx-input-image').getAttribute('src').then(src=>src.includes('/inputs/')));
  const sample=family.samples[0];
  await page.evaluate(id=>window.rfwExplorer.openAsset(id),sample);
  await page.waitForFunction(id=>document.querySelector('#gx-workbench').dataset.loaded===id,sample,{timeout:60000});
  await page.locator('#gx-workbench').scrollIntoViewIfNeeded();
  const asset=manifest.assets.find(a=>a.id===sample);
  ok(`${family.name}: source joints and every link selectable`,await page.locator('#gx-joint option').count()===asset.joints.length&&await page.locator('[data-part]').count()===asset.links+1);
  await page.locator('[data-part]').nth(1).click();
  ok(`${family.name}: part button highlights and shows source mass`,await page.locator('[data-part]').nth(1).getAttribute('aria-pressed')==='true'&&await page.locator('#gx-part-info').textContent().then(t=>t.includes('Part mass')));
  await page.locator('#gx-color').click();
  ok(`${family.name}: part colors enabled`,await page.locator('#gx-color').getAttribute('aria-pressed')==='true');
  const movable=await page.evaluate(()=>window.rfwExplorer.rig.findIndex(j=>!j.mimic&&j.upper>j.lower));
  if(movable>=0){
    await page.selectOption('#gx-joint',String(movable));
    const before=await page.evaluate(i=>window.rfwExplorer.rig[i].value,movable);
    await page.locator('#gx-position').fill('650');
    ok(`${family.name}: joint slider changes the model pose`,await page.evaluate(i=>window.rfwExplorer.rig[i].value,movable)!==before);
  }
  await page.locator('#gx-reset').click();
}
const clamp='Handtools_Clamp__0000';
await page.evaluate(id=>window.rfwExplorer.openAsset(id),clamp);
await page.waitForFunction(id=>document.querySelector('#gx-workbench').dataset.loaded===id,clamp);
await page.locator('#gx-workbench').scrollIntoViewIfNeeded();
await page.locator('[data-part="screw"]').click();
await page.locator('#gx-simulate').click();
await page.waitForFunction(()=>window.rfwExplorer.simulation||document.querySelector('#gx-simulate').textContent==='Retry simulation',{},{timeout:60000});
ok('Real MuJoCo initializes on demand',await page.evaluate(()=>Boolean(window.rfwExplorer.simulation)));
ok('Damped interaction applies the recorded fixture',await page.evaluate(()=>{
  const {simulation:s,details}=window.rfwExplorer;
  return s.stabilized&&details.simulation.interaction.joints.every(item=>s.model.dof_damping[s.mapping.find(j=>j.name===item.name).dof]===item.damping);
}));
await page.locator('#gx-damping').uncheck();
ok('Source dynamics can be restored',await page.evaluate(()=>{
  const s=window.rfwExplorer.simulation;
  return !s.stabilized&&s.mapping.every(j=>Math.abs(s.model.dof_damping[j.dof]-(j.damping||0))<1e-9);
}));
await page.locator('#gx-damping').check();
await page.locator('#gx-play').click();
await page.waitForFunction(()=>window.rfwExplorer.simulation.time>.05);
await page.locator('#gx-play').click();
const time=await page.evaluate(()=>window.rfwExplorer.simulation.time);
await page.waitForTimeout(200);
ok('Simulation advances and pauses',time>0&&await page.evaluate(()=>window.rfwExplorer.simulation.time)===time);
await page.locator('#gx-gravity').uncheck();
ok('Gravity toggle changes engine gravity',await page.evaluate(()=>window.rfwExplorer.simulation.model.opt.gravity[2])===0);
await page.locator('#gx-reset').click();
ok('Reset restores simulation state',await page.evaluate(()=>window.rfwExplorer.simulation.time)===0);
await page.locator('#gx-force-plus').click();
await page.waitForFunction(()=>window.rfwExplorer.simulation.time>.05);
ok('Joint push runs the physics engine',await page.evaluate(()=>window.rfwExplorer.simulation.positions().some(v=>Math.abs(v)>1e-7)));
await page.locator('#gx-play').click();
await page.locator('#gx-workbench').screenshot({path:'/tmp/rfw-explorer/explorer-inspector.png'});
ok('Excessive joint speed pauses without corrupting the pose',await page.evaluate(()=>{
  const s=window.rfwExplorer.simulation;
  s.data.qvel[s.mapping[0].dof]=1e8;s.running=true;
  try { s.step(.01); return false; } catch(error) {
    const stopped=!s.running&&s.positions().every(Number.isFinite)&&s.data.qvel.every(v=>v===0)&&error.message.includes('excessive joint speed');
    s.reset();return stopped;
  }
}));

const next=manifest.families[1].samples[1];
await page.evaluate(id=>window.rfwExplorer.openAsset(id),next);
await page.waitForFunction(id=>document.querySelector('#gx-workbench').dataset.loaded===id,next);
ok('Switching seeds releases the previous simulation',await page.evaluate(()=>window.rfwExplorer.simulation===null));
await page.reload({waitUntil:'networkidle'});
await page.waitForFunction(id=>document.querySelector('#gx-workbench').dataset.loaded===id,next,{timeout:60000});
ok('Sample URL restores the selected category and seed',await page.locator('[data-seed][aria-pressed=true]').getAttribute('data-seed')===next);
await page.evaluate(()=>{const ids=window.rfwExplorer.manifest.assets.slice(0,3).map(a=>a.id);return Promise.all(ids.map(id=>window.rfwExplorer.openAsset(id)));});
ok('Rapid asset switching leaves the latest selection active',await page.evaluate(()=>document.querySelector('#gx-workbench').dataset.loaded===window.rfwExplorer.selected.id));
for(const width of [390,320]){
  await page.setViewportSize({width,height:844});
  await page.locator('#gx-workbench').scrollIntoViewIfNeeded();
  ok(`${width}px layout fits viewport`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  if(width===390)await page.locator('#gx-workbench').screenshot({path:'/tmp/rfw-explorer/explorer-mobile.png'});
}
await page.goto(new URL('demo.html',base).href,{waitUntil:'networkidle'});
ok('Retired standalone demo leads to the unified explorer',page.url().includes('#dataset')&&await page.locator('#dataset').count()===1);
ok('No browser exceptions or missing resources',errors.length===0);
await writeFile('/tmp/rfw-explorer/browser-validation.json',JSON.stringify({checks,errors},null,2));
await browser.close();
