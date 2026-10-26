"""Prepare website media and public metadata from the supplied handoff. Sources stay read-only."""
import json,shutil,re,subprocess,pathlib
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parents[1]
HANDOFF=pathlib.Path('/tmp/brain/RFW_Web_Handoff_20261026/RFW_Web_Handoff_20261026')
PUB=ROOT/'public'; MEDIA=PUB/'media'
def image(src,dst,width=1600):
 im=Image.open(src).convert('RGB');im.thumbnail((width,width));im.save(MEDIA/dst,quality=87)
def video(src,dst):
 shutil.copy2(src,MEDIA/dst)
content=json.loads((HANDOFF/'handoff/website_content.json').read_text())
for s in content['scenes']:
 v=s['variants'][0];image(HANDOFF/v['poster'],s['scene_id']+'.webp')
 video(HANDOFF/v['video'],s['scene_id']+'.mp4')
video(pathlib.Path('/home/lyuyuanbo.lyb/2610261545030522.mp4'),'film.mp4')
video(HANDOFF/'public/demo/climax/asset_wall.mp4','asset-wall.mp4')
subprocess.run(['ffmpeg','-y','-ss','8','-i',str(MEDIA/'film.mp4'),'-frames:v','1',str(MEDIA/'film-poster.webp')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
for p in (HANDOFF/'public/demo/editing').glob('*/*.png'):
 image(p,'edit-'+p.parent.name+'-'+p.stem+'.webp',1200)
for p in (HANDOFF/'public/demo/sim2real-paper-20261014').glob('*.mp4'):
 video(p,p.name)
 subprocess.run(['ffmpeg','-y','-ss','0.2','-i',str(p),'-frames:v','1','-vf','scale=640:-1',str(MEDIA/(p.stem+'.webp'))],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
# Paper figures are exported from the current paper, without publishing the PDF.
for source,name in [('fig04_method_pipeline_N','method'),('teaser','dataset'),('fig06_material_grounding','materials'),('fig8','articulation')]:
 out=pathlib.Path('/tmp/rfw-web')/name
 subprocess.run(['pdftoppm','-singlefile','-scale-to','2400','-png',f'/home/lyuyuanbo.lyb/RFW_A_arxiv/figures/{source}.pdf',str(out)],check=True)
 image(out.with_suffix('.png'),name+'.webp',2400)
manifest=json.loads((HANDOFF/'assets/final/manifest.json').read_text())
label_map={'asset_90_hero_toaster':'Toaster','scene7_car_rec_qwen37v_car002_v11_2':'Car','swing_0970_placement':'Swing','tower_001':'Wind turbine','v03_lunar_rover_canopy':'Lunar rover','v03_satellite_articulated':'Satellite'}
assets=[]
for a in manifest['assets']:
 stem=a['asset_id'].rsplit('_',1)[0]
 label=label_map.get(stem)
 if not label:
  label=re.sub(r'^(asset_\d+_|urdf_\d+_|adjust_|v03_)','',stem).replace('_placement','').replace('_001','').replace('_',' ').capitalize()
 prov=json.loads((HANDOFF/a['provenance_file']).read_text())
 joints=[{'name':j.get('name',j.get('id','Joint')).split(' / ')[-1], 'type':j.get('type','unknown'),'lower':j.get('lower'),'upper':j.get('upper')} for j in prov['joints']]
 assets.append({'id':a['asset_id'],'name':label,'scene':a['scene_id'].replace('indoor_opening','indoor'),'joints':joints,'meshes':a['mesh_count'],'model':f"models/{a['asset_id']}.glb",'thumbnail':f"media/thumbs/{a['asset_id']}.webp",'sourceHash':a['blend_sha256'],'source':'Audited native scene asset','units':'meters'})
(PUB/'data/catalog.json').write_text(json.dumps(assets,indent=2))
(PUB/'data/resources.json').write_text(json.dumps({'paper':None,'code':None,'dataset':None},indent=2))
print('Prepared',len(assets),'assets and supplied research media.')
