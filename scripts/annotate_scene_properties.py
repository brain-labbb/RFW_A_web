"""Build part-level scene physics; preserve matched source fields and annotate missing ones.
Credentials stay outside the repo. Usage: python scripts/annotate_scene_properties.py /path/api.txt
"""
import ast,concurrent.futures,hashlib,json,math,pathlib,re,sys,time,urllib.request,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1];P=pathlib.Path('/tmp/brain/RFW_Web_Handoff_20261026/RFW_Web_Handoff_20261026');TMP=pathlib.Path('/tmp/rfw-scenes');AUDIT=ROOT/'offline/scene-physics-audit';AUDIT.mkdir(parents=True,exist_ok=True);OUT=ROOT/'public/data/scene-physics';OUT.mkdir(parents=True,exist_ok=True)
config=ast.parse(pathlib.Path(sys.argv[1]).read_text());cred={k.arg:ast.literal_eval(k.value) for n in ast.walk(config) if isinstance(n,ast.Call) for k in n.keywords if k.arg in ('api_key','base_url') and isinstance(k.value,ast.Constant)}
manifest={a['asset_id']:a for a in json.loads((P/'assets/final/manifest.json').read_text())['assets']};catalog={a['id']:a for a in json.loads((ROOT/'public/data/catalog.json').read_text())};selected=[a['id'] for g in json.loads((ROOT/'scripts/scene_shots.json').read_text()).values() for a in g];native={a['id']:a for sid in ['indoor','outdoor','space','laboratory'] for a in json.loads((TMP/(sid+'-expansion.json')).read_text())}
def number(e,key):
 try:
  v=float(e.get(key)) if e is not None else None
  return v if v is not None and math.isfinite(v) else None
 except (ValueError,TypeError):return None
def simple(s):return re.sub(r'[^a-z0-9]','',s.lower())
def run(aid):
 a=manifest[aid];n=native[aid];prov=json.loads((P/a['provenance_file']).read_text());source=None;sourcepath=None
 candidates=[f for f in a['original_source_candidates'] if f.endswith('.urdf') and (P/f).exists()]
 # Ambiguous original seeds are provenance only; do not silently choose one.
 if len(candidates)==1:sourcepath=candidates[0];source=ET.parse(P/sourcepath).getroot()
 slinks={x.get('name'):x for x in source.findall('link')} if source is not None else {};sjoints={x.get('name'):x for x in source.findall('joint')} if source is not None else {}
 children={x.find('child').get('link') for x in sjoints.values()};rootlinks=[k for k in slinks if k not in children]
 parts=[]
 for i,g in enumerate(n['parts']):
  raw=g['name'];jointname=re.sub(r'\.(?:revolute|continuous|prismatic|fixed)\.bone$','',raw);j=sjoints.get(jointname);linkname=j.find('child').get('link') if j is not None else None
  if linkname is None:
   matches=[k for k in slinks if simple(raw.split(' / ')[-1])==simple(k)]
   if len(matches)==1:linkname=matches[0]
   elif raw in ['root','root.bone',a['root_object']] and len(rootlinks)==1:linkname=rootlinks[0]
  link=slinks.get(linkname);mass=number(link.find('inertial/mass'),'value') if link is not None else None
  inertia={k:number(link.find('inertial/inertia'),k) for k in ['ixx','iyy','izz','ixy','ixz','iyz']} if link is not None else None
  if not inertia or any(v is None for v in inertia.values()) or min(inertia['ixx'],inertia['iyy'],inertia['izz'])<=0:inertia=None
  origin=link.find('inertial/origin') if link is not None else None
  com=[float(x) for x in origin.get('xyz','0 0 0').split()] if origin is not None else ([0,0,0] if inertia else None)
  rotation=[float(x) for x in origin.get('rpy','0 0 0').split()] if origin is not None else [0,0,0]
  name=linkname or re.sub(r'\.(?:revolute|continuous|prismatic|fixed)\.bone$','',raw).split(' / ')[-1]
  name='body' if name in [a['root_object'],'root','root.bone'] else name
  parts.append({'id':str(i),'name':name.replace('_',' '),'materials':g['materials'],'massKg':mass if mass is not None and mass>0 else None,'massOrigin':'source' if mass is not None and mass>0 else None,'centerOfMass':com,'inertia':inertia,'inertiaOrigin':'source' if inertia else None,'inertialRotation':rotation,'dimensions_m':g['dimensions_m'],'bounds':g['bounds'],'sourceLink':linkname,'meshes':g['meshes']})
 # A source link can own several detached native groups (e.g. a repaired shell).
 # Merge those groups so its source mass/inertia is never counted twice.
 merged={}
 for part in parts:
  key=part['sourceLink'] or 'native:'+part['id']
  if key not in merged:merged[key]=part;continue
  old=merged[key];old['materials']=sorted(set(old['materials']+part['materials']));old['meshes']+=part['meshes']
  old['bounds']=[[min(old['bounds'][0][i],part['bounds'][0][i]) for i in range(3)],[max(old['bounds'][1][i],part['bounds'][1][i]) for i in range(3)]]
  old['dimensions_m']=[old['bounds'][1][i]-old['bounds'][0][i] for i in range(3)]
 parts=list(merged.values())
 for i,part in enumerate(parts):part['id']=str(i)
 joints=[]
 for i,j in enumerate(catalog[aid]['joints']):
  if j['type']=='fixed':continue
  x=sjoints.get(j['name']);pj=next((v for v in prov['joints'] if v['name'].split(' / ')[-1]==j['name'] or v.get('properties',{}).get('joint_name')==j['name']),None)
  if pj and pj.get('properties',{}).get('source_joint_xml'):
   try:x=ET.fromstring(pj['properties']['source_joint_xml'])
   except ET.ParseError:pass
  fields={k:number(x.find(tag),k) if x is not None else None for tag,keys in [('limit',['effort','velocity']),('dynamics',['damping','friction'])] for k in keys}
  joints.append({**j,'id':str(i),**fields,'origins':{k:'source' if v is not None else None for k,v in fields.items()}})
 missingparts=[{'id':p['id'],'name':p['name'],'dimensions_m':p['dimensions_m'],'materials':p['materials']} for p in parts if p['massKg'] is None]
 missingjoints=[{'id':j['id'],'name':j['name'],'type':j['type'],'lower':j.get('lower'),'upper':j.get('upper'),'missing':[k for k in ['effort','velocity','damping','friction'] if j[k] is None]} for j in joints if any(j[k] is None for k in ['effort','velocity','damping','friction'])]
 prompt={'asset':catalog[aid]['name'],'dimensions_m':[n['bounds'][1][i]-n['bounds'][0][i] for i in range(3)],'known_mass_kg':sum(p['massKg'] or 0 for p in parts),'parts_missing_mass':missingparts,'joints_missing_parameters':missingjoints,'task':'Estimate missing engineering parameters for this articulated asset. Parts are physical groups of meshes. Estimate realistic mass accounting for hollow construction, not solid bounding-box density. Keep repeated parts consistent. Joint parameters in SI: prismatic effort/friction N, velocity m/s, damping N*s/m; rotational effort/friction N*m, velocity rad/s, damping N*m*s/rad. Return JSON {parts:[{id,massKg,centerFraction:[cx,cy,cz],varianceFactors:[vx,vy,vz],basis}],joints:[{id,values:{only requested missing fields},basis}]}. For each part also estimate its center of mass as fractions of its axis-aligned bounds (0..1), and diagonal mass-distribution variances divided by squared axis extent. For each axis use 0 < varianceFactor <= centerFraction*(1-centerFraction); a uniform box has 1/12, a thin shell or concentrated hardware may differ. Use current part dimensions and materials to choose plausible hollow/solid distributions. These will produce a diagonal inertia approximation aligned with the scene axes, using Ixx=m*(vy*dy^2+vz*dz^2), etc. Do not assume every part is a uniform solid box. Every requested id exactly once; positive finite mass, effort, velocity; nonnegative damping/friction. Estimates, not measurements. Concise basis in English.'}
 fingerprint=hashlib.sha256(json.dumps(prompt,sort_keys=True).encode()).hexdigest();cache=AUDIT/(aid+'.json');result=None
 if cache.exists():
  old=json.loads(cache.read_text())
  if old.get('fingerprint')==fingerprint:result=old
 if result is None:
  payload={'model':'qwen3.8-max','reasoning_effort':'medium','messages':[{'role':'system','content':'You annotate physical parameters for articulated 3D assets. Return strictly valid JSON. Return exactly the requested ids. If parts_missing_mass is empty, parts MUST be an empty array. If joints_missing_parameters is empty, joints MUST be an empty array.'},{'role':'user','content':json.dumps(prompt)}],'response_format':{'type':'json_object'},'max_tokens':32000}
  for attempt in range(4):
   try:
    req=urllib.request.Request(cred['base_url'].rstrip('/')+'/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+cred['api_key'],'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=600) as r:response=json.load(r)
    result=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',response['choices'][0]['message']['content'].strip()))
    (AUDIT/(aid+'-last-response.json')).write_text(json.dumps(result,indent=2))
    assert {str(v['id']) for v in result['parts']}=={v['id'] for v in missingparts}
    assert {str(v['id']) for v in result['joints']}=={v['id'] for v in missingjoints}
    for v in result['parts']:
     assert isinstance(v['massKg'],(float,int)) and math.isfinite(v['massKg']) and v['massKg']>0
     assert len(v['centerFraction'])==len(v['varianceFactors'])==3
     for c,f in zip(v['centerFraction'],v['varianceFactors']):assert math.isfinite(c) and math.isfinite(f) and 0<c<1 and 0<f<=c*(1-c)+1e-7
    for v in result['joints']:
     wanted=next(j['missing'] for j in missingjoints if j['id']==str(v['id']))
     for k in wanted:assert isinstance(v['values'][k],(float,int)) and math.isfinite(v['values'][k]) and (v['values'][k]>0 if k in ['effort','velocity'] else v['values'][k]>=0)
    result.update({'fingerprint':fingerprint,'model':response.get('model'),'reasoning_effort':'medium','usage':response.get('usage')});cache.write_text(json.dumps(result,indent=2));break
   except Exception as e:
    if attempt==3:raise
    print('RETRY',aid,type(e).__name__,flush=True);time.sleep(3*(attempt+1))
 bypart={str(p['id']):p for p in result['parts']};byjoint={str(j['id']):j for j in result['joints']}
 for p in parts:
  if p['massKg'] is None:p.update(massKg=bypart[p['id']]['massKg'],massOrigin='qwen_estimate',massBasis=bypart[p['id']].get('basis',''))
  if p['inertia'] is None:
   annotation=bypart[p['id']];variances=[f*max(d,.0001)**2 for f,d in zip(annotation['varianceFactors'],p['dimensions_m'])];x,y,z=variances;m=p['massKg'];p['inertia']={'ixx':m*(y+z),'iyy':m*(x+z),'izz':m*(x+y),'ixy':0,'ixz':0,'iyz':0};p['centerOfMass']=[p['bounds'][0][i]+annotation['centerFraction'][i]*p['dimensions_m'][i] for i in range(3)];p['inertiaOrigin']='qwen_estimate';p['inertialRotation']=[0,0,0];p['inertiaFrame']='Scene axes, at estimated center of mass; center position in scene coordinates (reference frame).';p['inertiaBasis']='Diagonal approximation from Qwen-estimated mass distribution: '+annotation.get('basis','')
  else:p['inertiaFrame']='Source inertial frame; center position and RPY in source link coordinates.'
  p.pop('bounds');p.pop('meshes')
 for j in joints:
  for k in ['effort','velocity','damping','friction']:
   if j[k] is None:j[k]=byjoint[j['id']]['values'][k];j['origins'][k]='qwen_estimate'
 # Reuse the already audited material labels for readable part descriptions.
 materialfile=ROOT/'public/data/physics'/(aid+'.json')
 labels={m['surfaceMaterial']:m['material'] for m in json.loads(materialfile.read_text())['materials']} if materialfile.exists() else {}
 for part in parts:
  part['surfaceMaterials']=part['materials'];part['materials']=list(dict.fromkeys(labels.get(m,m) for m in part['materials']))
  part['name']=re.sub(r'^.*? to ', '', part['name'])
 bread_index=0
 for part in parts:
  if re.match(r'^mask \d+ object$',part['name']) and any('bread' in m.lower() for m in part['materials']):
   bread_index+=1;part['name']=f'Bread slice {bread_index}'
 parts.sort(key=lambda p:p['massKg'],reverse=True)
 out={'assetId':aid,'name':catalog[aid]['name'],'totalMassKg':sum(p['massKg'] for p in parts),'instanceCount':1,'parts':parts,'joints':joints,'annotationModel':'qwen3.8-max','reasoningEffort':'medium','sourceUrdf':sourcepath,'referenceFrame':240 if catalog[aid]['scene']=='space' else 1,'note':'Source parameters are retained when uniquely matched. Estimated masses and missing joint dynamics: Qwen3.8-Max (medium). Missing inertias: diagonal approximation from Qwen-estimated mass distribution within native part bounds; not measured.'}
 (OUT/(aid+'.json')).write_text(json.dumps(out,indent=2));print('READY',aid,len(parts),'parts',len(joints),'joints',flush=True)
if '--only' in sys.argv:selected=[sys.argv[sys.argv.index('--only')+1]]
errors=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 futures={pool.submit(run,a):a for a in selected}
 for f in concurrent.futures.as_completed(futures):
  try:f.result()
  except Exception as e:errors.append({'id':futures[f],'error':type(e).__name__+': '+str(e)});print('FAILED',futures[f],type(e).__name__,str(e),flush=True)
(AUDIT/'summary.json').write_text(json.dumps({'assets':len(selected),'errors':errors,'model':'qwen3.8-max','reasoning_effort':'medium'},indent=2))
if errors:sys.exit(1)
