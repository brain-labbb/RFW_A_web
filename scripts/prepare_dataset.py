"""Select a small, auditable slice of PV_A_vlm. Does not alter or enumerate the full dataset."""
from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET,concurrent.futures,re
ROOT=Path(__file__).resolve().parents[1];SOURCE=Path('/data/oss_bucket_0/yuanbo/PV_A_vlm/assets')
FAMILIES=[
 ('ceiling_fan','Ceiling fans','Home',[0,1,5,7],'Blade assemblies, housing, and proportions vary while the rotor remains articulated.'),
 ('drawer_cabinet_with_sliding_drawers','Drawer cabinets','Home',[0,1,16,4],'Repeated drawers change the part hierarchy and the number of sliding joints.'),
 ('satellite_with_articulated_solar_panels','Satellites','Space',[0,1,3,7],'Solar-wing configurations change while their hinged connections are retained.'),
 ('ferris_wheel','Ferris wheels','Outdoor',[0,1,3,5],'The wheel and repeated gondolas form articulated assemblies of different complexity.')]
EXTRAS=[('Astronomy_Mars_rover','Mars rover','Space'),('Astronomy_Astronaut_helmet','Astronaut helmet','Space'),('Handtools_Knife','Knife','Tools'),('Handtools_Paint_roller','Paint roller','Tools'),('Industrial_Drill_press_table','Drill press table','Industry'),('Healthcare_Prosthetic_limb','Prosthetic limb','Healthcare'),('Playground_swing','Playground swing','Outdoor'),('sewing_machine','Sewing machine','Home')]
def get(job):
 cat,name,domain,seed=job;p=SOURCE/cat/f'seed_{seed:04d}';raw=(p/'model.urdf').read_bytes();t=ET.fromstring(raw);a=json.loads((p/'appearance.json').read_text());bindings=a.get('bindings',[])
 joints=[]
 for j in t.findall('joint'):
  if j.get('type')=='fixed':continue
  limit=j.find('limit');axis=j.find('axis');joints.append({'name':j.get('name'),'type':j.get('type'),'lower':float(limit.get('lower','0')) if limit is not None else 0,'upper':float(limit.get('upper','0')) if limit is not None else 0,'axis':list(map(float,axis.get('xyz','1 0 0').split())) if axis is not None else [1,0,0]})
 meshes=[]
 for m in t.findall('.//mesh'):
  f=m.get('filename');q=p/f
  if not q.is_file():raise ValueError('Missing mesh: '+str(q))
  meshes.append(f)
 classes=sorted(set(b.get('material_class_id') for b in bindings if b.get('material_class_id')))
 aid=f'{cat}__{seed:04d}'
 visuals=[v.get('name','') for v in t.findall('link/visual')]
 features=[]
 if cat=='ceiling_fan':
  blades=set(re.findall(r'blade_(\d+)', ' '.join(visuals)));features.append(f'{len(blades)} blades')
 if cat=='drawer_cabinet_with_sliding_drawers':features.append(f"{sum(j['type']=='prismatic' for j in joints)} sliding joints")
 if cat=='satellite_with_articulated_solar_panels':
  wings=[l.get('name') for l in t.findall('link') if 'wing' in l.get('name','')];features.append(f'{len(wings)} wing links')
 if cat=='ferris_wheel':
  gondolas=[l.get('name') for l in t.findall('link') if 'gondola' in l.get('name','').lower()];features.append(f'{len(gondolas)} gondola links')
 return {'id':aid,'category':cat,'name':name,'domain':domain,'seed':seed,'templateHash':a['template_sha256'],'urdfHash':hashlib.sha256(raw).hexdigest(),'appearanceHash':hashlib.sha256((p/'appearance.json').read_bytes()).hexdigest(),'links':len(t.findall('link')),'joints':joints,'surfaces':len(visuals),'materialClasses':classes,'materialEntries':len(set((b.get('material') or {}).get('material_id') for b in bindings if (b.get('material') or {}).get('material_id'))),'features':features,'image':f'media/dataset/{aid}.webp','model':f'models/dataset/{aid}.glb','sourceRelative':f'{cat}/seed_{seed:04d}','sourceBindings':len(bindings)}
jobs=[(c,n,d,s) for c,n,d,seeds,_ in FAMILIES for s in seeds]+[(c,n,d,0) for c,n,d in EXTRAS]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:assets=list(pool.map(get,jobs))
families=[]
for c,n,d,seeds,desc in FAMILIES:
 members=[a for a in assets if a['category']==c];hashes=set(a['templateHash'] for a in members)
 assert len(hashes)==1, f'{c}: mixed generator versions'
 families.append({'id':c,'name':n,'description':desc,'templateHash':members[0]['templateHash'],'samples':[a['id'] for a in members]})
out={'release':{'assets':402410,'categories':531,'source':'RFW_A_arxiv, dataset section and Tables 1–2'},'scope':'Curated representative examples; not a full dataset browser.','source':'PV_A_vlm/assets','families':families,'assets':assets,'gallery':[a['id'] for a in assets if a['seed']==0]}
p=ROOT/'public/data/dataset.json';p.write_text(json.dumps(out,indent=2));print('Selected',len(assets),'samples /',len(set(a['category'] for a in assets)),'categories')
