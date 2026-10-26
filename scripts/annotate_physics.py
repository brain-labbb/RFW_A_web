"""Offline Qwen material annotation. Credentials are read from an external 0600 file.
Never run this in a browser; source assets are read-only. Cached API results allow resume.
"""
import json,pathlib,urllib.request,time,concurrent.futures,sys,math,re
ROOT=pathlib.Path(__file__).resolve().parents[1]
HANDOFF=pathlib.Path('/tmp/brain/RFW_Web_Handoff_20261026/RFW_Web_Handoff_20261026')
PRIVATE=ROOT/'offline/physics-audit';PRIVATE.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'public/data/physics';OUT.mkdir(exist_ok=True)
credential=json.loads(pathlib.Path(sys.argv[1]).read_text())
MODEL='qwen3.8-max'
keys=['density_kg_m3','youngs_modulus_pa','poissons_ratio','static_friction_coefficient','dynamic_friction_coefficient','restitution_coefficient']
sources=dict(json.loads((ROOT/'offline/physics-sources.json').read_text()))
assets=json.loads((ROOT/'offline/current-materials.json').read_text())
def valid(v):
 return all(isinstance(v.get(k),(int,float)) and math.isfinite(v[k]) for k in keys) and v[keys[0]]>0 and v[keys[1]]>0 and -1<v[keys[2]]<0.5 and 0<=v[keys[4]]<=v[keys[3]]<=3 and 0<=v[keys[5]]<=1
def run(a):
 aid=a['id']; cache=PRIVATE/(aid+'.json')
 groups={}
 for s in a['surfaces']:
  for m in s['materials']:
   if m['name'] not in groups:groups[m['name']]={'id':str(len(groups)),'material':m,'parts':[]}
   groups[m['name']]['parts'].append(s['name'])
 refs={}
 for f in sources.get(aid,[]):
  for b in json.loads((HANDOFF/f).read_text()).get('bindings',[]):
   if valid(b.get('values',{})):
    label=b.get('material_class_id') or 'unknown'
    refs[label]=b['values']
 # Retain direct material-name matches only; refined or unbound materials need annotation.
 known=[];missing=[]
 for g in groups.values():
  text=g['material']['name'].lower()
  match=next((k for k in refs if k in text),None)
  if match:known.append({'id':g['id'],'name':match.replace('.',' / ').replace('_',' '),'values':refs[match],'origin':'source_library'})
  else:missing.append(g)
 if cache.exists(): result=json.loads(cache.read_text())
 elif missing:
  prompt={'asset':a['label'],'dimensions_m':a['dimensions_m'],'materials':missing,'existing_source_reference':refs,
    'task':'Annotate missing material physical properties for current Blender scene materials. Use material names, PBR channels and associated mesh parts. Existing source reference may be reused only for matching material substance. If material identity is ambiguous, select a plausible engineering substance. Use bulk substrate properties for coated surfaces. Friction and restitution assume dry self-contact at room temperature, moderate impact speed. Return compact JSON object with materials array, exactly one entry per requested id: {id,name (short readable English material label),values:{density_kg_m3,youngs_modulus_pa,poissons_ratio,static_friction_coefficient,dynamic_friction_coefficient,restitution_coefficient},basis (brief internal assumption)}. All values numeric SI, static friction >= dynamic friction >=0, 0<=restitution<=1, -1<poissons_ratio<0.5, positive density/modulus. These are estimates, not measurements. Do not infer mass from bounding-box volume. No markdown.'}
  body={'model':MODEL,'messages':[{'role':'system','content':'You annotate engineering materials. Return only valid JSON and respect the requested schema.'},{'role':'user','content':json.dumps(prompt)}],'temperature':0.1,'enable_thinking':False,'max_tokens':12000,'response_format':{'type':'json_object'}}
  for attempt in range(3):
   try:
    request=urllib.request.Request(credential['base_url']+'/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+credential['api_key'],'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=180) as r:response=json.load(r)
    text=response['choices'][0]['message']['content'].strip()
    result=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',text))
    if {str(x['id']) for x in result['materials']}!={g['id'] for g in missing}:raise ValueError('Material coverage mismatch')
    if not all(valid(x['values']) for x in result['materials']):raise ValueError('Invalid physical values')
    result.update({'model':response.get('model',MODEL),'usage':response.get('usage'),'asset_id':aid})
    cache.write_text(json.dumps(result,indent=2));break
   except Exception as e:
    if attempt==2:raise
    time.sleep(2*(attempt+1))
 else: result={'materials':[]}
 byid={str(m['id']):m for m in result['materials']+known}
 out=[]
 for g in groups.values():
  m=byid[g['id']]
  out.append({'id':g['id'],'material':m['name'],'surfaceMaterial':g['material']['name'],'parts':g['parts'],'values':{k:m['values'][k] for k in keys}})
 (OUT/(aid+'.json')).write_text(json.dumps({'assetId':aid,'dimensions_m':a['dimensions_m'],'materials':out},indent=2))
 print('READY',aid,len(out),'materials',flush=True)
 return len(out)
errors=[];total=0
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 futures={pool.submit(run,a):a for a in assets}
 for f in concurrent.futures.as_completed(futures):
  try:total+=f.result()
  except Exception as e:
   aid=futures[f]['id'];errors.append({'asset':aid,'error':str(e)});print('FAILED',aid,type(e).__name__,str(e),flush=True)
(PRIVATE/'summary.json').write_text(json.dumps({'assets':len(assets),'material_groups':total,'errors':errors,'model':MODEL},indent=2))
print('COMPLETE',total,'material groups;',len(errors),'errors',flush=True)
