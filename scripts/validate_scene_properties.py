"""Validate scene coverage, mass accounting and physical tensors independently."""
import json,math,pathlib,collections
ROOT=pathlib.Path(__file__).resolve().parents[1];shots=json.loads((ROOT/'scripts/scene_shots.json').read_text());counts=collections.Counter()
for shot in [a for group in shots.values() for a in group]:
 a=json.loads((ROOT/'public/data/scene-physics'/(shot['id']+'.json')).read_text());assert a['assetId']==shot['id'];assert a['annotationModel']=='qwen3.8-max' and a['reasoningEffort']=='medium';assert a['parts'] and a['joints']
 assert math.isclose(a['totalMassKg'],sum(p['massKg'] for p in a['parts']),rel_tol=1e-9)
 links=[p['sourceLink'] for p in a['parts'] if p['sourceLink']];assert len(links)==len(set(links)),(a['assetId'],'duplicate source mass')
 for p in a['parts']:
  assert p['inertiaOrigin'] in ['source','qwen_estimate'];assert math.isfinite(p['massKg']) and p['massKg']>0;assert p['materials'];assert len(p['centerOfMass'])==3 and all(math.isfinite(x) for x in p['centerOfMass'])
  t=p['inertia'];x,y,z,xy,xz,yz=[t[k] for k in ['ixx','iyy','izz','ixy','ixz','iyz']];assert all(math.isfinite(v) for v in t.values());assert min(x,y,z)>0
  tol=max(x,y,z)**3*1e-8
  assert x*y-xy*xy>=-tol and x*z-xz*xz>=-tol and y*z-yz*yz>=-tol,(a['assetId'],p['name'],'principal minor')
  assert x*y*z+2*xy*xz*yz-x*yz*yz-y*xz*xz-z*xy*xy>=-tol,(a['assetId'],p['name'],'tensor determinant')
  assert max(x,y,z)<=sum([x,y,z])-max(x,y,z)+max(x,y,z)*1e-6,(a['assetId'],p['name'],'inertia triangle')
  counts['parts']+=1;counts['mass_'+p['massOrigin']]+=1;counts['inertia_'+p['inertiaOrigin']]+=1
 for j in a['joints']:
  for k in ['effort','velocity','damping','friction']:
   assert isinstance(j[k],(int,float)) and math.isfinite(j[k]);assert j[k]>0 if k in ['effort','velocity'] else j[k]>=0;assert j['origins'][k] in ['source','qwen_estimate'];counts[k+'_'+j['origins'][k]]+=1
  counts['joints']+=1
 counts['assets']+=1
report={'status':'pass',**dict(counts)};print(json.dumps(report,indent=2));pathlib.Path('/tmp/rfw-scenes/physics-validation.json').write_text(json.dumps(report,indent=2))
