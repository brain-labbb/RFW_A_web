import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:1050}});
page.on('pageerror',e=>console.log('PAGEERROR:',e.message));
page.on('console',m=>{if(m.type()==='error')console.log('CONSOLE-ERR:',m.text().slice(0,300));});
await page.goto(process.env.TEST_URL||'http://127.0.0.1:4173/',{waitUntil:'networkidle'});
await page.locator('#editing').scrollIntoViewIfNeeded();
await page.waitForFunction(()=>window.__editingReady,null,{timeout:60000});
await page.waitForFunction(()=>window.rfwEditing?.newView?.model,null,{timeout:60000});
await page.waitForTimeout(1500);
await page.locator('#editing').screenshot({path:'/tmp/rfw-editing/01-default.png'});
// size axis (fixed frame check: pick widest cabinet)
await page.locator('#edit3d-kinds [data-k="size"]').click();
await page.waitForTimeout(1200);
await page.locator('#editing').screenshot({path:'/tmp/rfw-editing/02-size.png'});
// material axis with grouped sub-axes
await page.locator('#edit3d-kinds [data-k="material"]').click();
await page.waitForTimeout(1200);
await page.locator('#editing').screenshot({path:'/tmp/rfw-editing/03-material.png'});
// switch object: fence, count 10
await page.locator('#edit3d-objects button').nth(1).click();
await page.waitForFunction(()=>window.rfwEditing?.object?.id==='fence',null,{timeout:60000});
await page.locator('#edit3d-kinds [data-k="count"]').click();
await page.waitForTimeout(500);
await page.locator('#edit3d-values button').last().click();
await page.waitForTimeout(1800);
await page.locator('#editing').screenshot({path:'/tmp/rfw-editing/04-fence-count10.png'});
// ferris wheel
await page.locator('#edit3d-objects button').nth(2).click();
await page.waitForTimeout(2000);
await page.locator('#editing').screenshot({path:'/tmp/rfw-editing/05-ferris.png'});
console.log('shots done');
await browser.close();
