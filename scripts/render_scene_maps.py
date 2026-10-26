"""Render a stable scene map and project audited native object bounds into it."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).parent))
from extend_space_stage import extend_space_stage
P=Path('/tmp/brain/RFW_Web_Handoff_20261026/RFW_Web_Handoff_20261026');O=Path('/tmp/rfw-scenes');sid=sys.argv[-1];v=next(s for s in json.loads((P/'handoff/website_content.json').read_text())['scenes'] if s['scene_id']==sid)['variants'][0];assets={a['asset_id']:a for a in json.loads((P/'assets/final/manifest.json').read_text())['assets']};shots=json.loads((Path(__file__).parent/'scene_shots.json').read_text())[sid]
bpy.ops.wm.open_mainfile(filepath=str(P/v['source_blend']));s=bpy.context.scene;s.frame_set(240 if sid=='space' else 1)
if sid=='space':
 extend_space_stage()
 s.camera.data.clip_end=10000
s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100;s.render.engine='CYCLES';s.cycles.device='GPU';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=6
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
def hull(points):
 points=sorted(set(points))
 def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
 lo=[];hi=[]
 for p in points:
  while len(lo)>1 and cross(lo[-2],lo[-1],p)<=0:lo.pop()
  lo.append(p)
 for p in reversed(points):
  while len(hi)>1 and cross(hi[-2],hi[-1],p)<=0:hi.pop()
  hi.append(p)
 return lo[:-1]+hi[:-1]
items=[];deps=bpy.context.evaluated_depsgraph_get()
for a in shots:
 prov=json.loads((P/assets[a['id']]['provenance_file']).read_text());points=[]
 for name in prov['visual_mesh_objects']:
  o=bpy.data.objects[name].evaluated_get(deps)
  for b in o.bound_box:
   c=world_to_camera_view(s,s.camera,o.matrix_world@Vector(b))
   if c.z>0:points.append((round(max(0,min(1,c.x)),5),round(max(0,min(1,1-c.y)),5)))
 poly=hull(points);pin=[(min(p[i] for p in poly)+max(p[i] for p in poly))/2 for i in range(2)];items.append({'id':a['id'],'pin':pin,'polygon':poly})
(O/(sid+'-map.json')).write_text(json.dumps(items,indent=2));s.render.image_settings.file_format='PNG';s.render.filepath=str(O/(sid+'-map.png'));bpy.ops.render.render(write_still=True)
print('MAP_READY',sid,flush=True)
