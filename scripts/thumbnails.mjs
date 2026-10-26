// Render catalog previews from the exact browser assets, not replacement models.
import {chromium} from 'playwright';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
const root=new URL('../',import.meta.url);const catalog=JSON.parse(await readFile(new URL('public/data/catalog.json',root),'utf8'));
await mkdir(new URL('public/media/thumbs/',root),{recursive:true});
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1200,height:950},deviceScaleFactor:1});
await page.goto('http://127.0.0.1:4173',{waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>window.__viewerReady,{timeout:60000});await page.locator('#explore').scrollIntoViewIfNeeded();
await page.addStyleTag({content:'.viewer-toolbar,.viewer-hint,.viewer-loading{visibility:hidden!important} #model-viewer{width:400px!important;height:320px!important}'});
const report=[];
for(const a of catalog){
 try{
  await page.evaluate(id=>window.rfw.selectAsset(id),a.id);await page.waitForFunction(id=>window.__viewerReady===id,a.id,{timeout:60000});
  await page.evaluate(()=>{window.rfw.viewer.resize();window.rfw.viewer.seek(0);});await page.waitForTimeout(150);
  const info=await page.evaluate(()=>({duration:window.rfw.viewer.duration,tracks:window.rfw.viewer.clips.reduce((n,c)=>n+c.tracks.length,0)}));
  const png=await page.locator('#model-viewer canvas').screenshot();
  const path=new URL('public/media/thumbs/'+a.id+'.webp',root).pathname;
  execFileSync('python',['-c',"import sys,io;from PIL import Image;Image.open(io.BytesIO(sys.stdin.buffer.read())).convert('RGB').save(sys.argv[1],quality=86)",path],{input:png});report.push({id:a.id,...info});console.log('THUMB',a.id,JSON.stringify(info));
 }catch(e){console.log('FAILED',a.id,e.message);report.push({id:a.id,error:e.message});}
}
await writeFile('/tmp/rfw-web/model-validation.json',JSON.stringify(report,null,2));await browser.close();
