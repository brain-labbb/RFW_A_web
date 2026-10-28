import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:1050}});
page.on('pageerror',e=>console.log('PAGEERROR:',e.message));
page.on('console',m=>{if(m.type()==='error')console.log('CONSOLE-ERR:',m.text().slice(0,300));});
await page.goto(process.env.TEST_URL||'http://127.0.0.1:4173/',{waitUntil:'networkidle'});
await page.locator('#editing').scrollIntoViewIfNeeded();
await page.waitForFunction(()=>window.__editingReady,{timeout:60000});
await page.waitForFunction(()=>window.rfwEditing?.newView?.model,{timeout:60000});
await page.waitForTimeout(1500);
await page.locator('#editing').screenshot({path:'/tmp/rfw-editing/01-default.png'});
// size axis (fixed frame check: pick widest cabinet)
await page.locator('#edit3d-kinds [data-k="size"]').click();
await page.waitForTimeout(1200);
await page.locator('#editing').screenshot({path:'/tmp/rfw-editing/02-size.png'});
// material axis with sub-axes
await page.locator('#edit3d-kinds [data-k="material"]').click();
await page.waitForTimeout(1200);
await page.locator('#editing').screenshot({path:'/tmp/rfw-editing/03-material.png'});
// switch object: fence, count 10
await page.locator('#edit3d-objects button').nth(1).click();
await page.waitForFunction(()=>window.rfwEditing?.object?.id==='fence');
await page.locator('#edit3d-kinds [data-k="count"]').click();
await page.waitForTimeout(500);
await page.locator('#edit3d-variants button').last().click();
await page.waitForTimeout(1800);
await page.locator('#editing').screenshot({path:'/tmp/rfw-editing/04-fence-count10.png'});
// ferris wheel
await page.locator('#edit3d-objects button').nth(2).click();
await page.waitForTimeout(2000);
await page.locator('#editing').screenshot({path:'/tmp/rfw-editing/05-ferris.png'});

// --- live mode (cabinet is the default object; switch back first) ---
await page.locator('#edit3d-objects button').nth(0).click();
await page.waitForFunction(()=>window.rfwEditing?.object?.id==='cabinet_paper_showcase');
const checks=[];
const ok=(n,c)=>{if(!c)throw new Error('LIVE CHECK FAILED: '+n);checks.push(n);console.log('PASS',n);};
ok('Live button visible on cabinet',await page.locator('#edit3d-live').isVisible());
await page.locator('#edit3d-live').click();
await page.waitForFunction(()=>window.rfwEditing?.live?.on===true,null,{timeout:180000});
ok('Live runtime loads and enables',true);
await page.waitForFunction(()=>window.rfwEditing?.live?.seq>=1&&window.rfwEditing?.newView?.model,null,{timeout:60000});
ok('Live base build renders',true);
const seq1=await page.evaluate(()=>window.rfwEditing.live.seq);
await page.locator('#edit3d-kinds [data-k="count"]').click();
await page.locator('#edit3d-variants button').last().click();
await page.waitForFunction(s=>window.rfwEditing.live.seq>s,seq1,{timeout:60000});
ok('Live count rebuild (4 doors)',(await page.locator('#edit3d-code').textContent()).includes('door_count: 2 → 4'));
await page.locator('#edit3d-kinds [data-k="size"]').click();
ok('Width slider appears in live size axis',await page.locator('#edit3d-slider').isVisible());
const seq2=await page.evaluate(()=>window.rfwEditing.live.seq);
await page.locator('#edit3d-width').fill('1.33');
await page.waitForFunction(s=>window.rfwEditing.live.seq>s,seq2,{timeout:60000});
await page.waitForTimeout(500);
const readout=await page.locator('#edit3d-code').textContent();
ok('Combination edit: width AND count accumulated',readout.includes('carcass_width_m: 1 → 1.33')&&readout.includes('door_count: 2 → 4'));
await page.locator('#editing').screenshot({path:'/tmp/rfw-editing/06-live-combo.png'});
await page.locator('#edit3d-prompt').fill('0.83');await page.locator('#edit3d-prompt-form button[type=submit]').click();
await page.waitForTimeout(1000);
ok('Prompt sets arbitrary live width',(await page.locator('#edit3d-code').textContent()).includes('0.83'));
await page.locator('#edit3d-live').click();
ok('Live off restores precomputed',await page.evaluate(()=>window.rfwEditing.live.on===false));
await page.locator('#edit3d-objects button').nth(1).click();
ok('Live button hidden on non-cabinet objects',!(await page.locator('#edit3d-live').isVisible()));
console.log('live checks passed:',checks.length);
await browser.close();
