"""Inspect native scene geometry and plan additional camera clips (Blender)."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1];P=Path('/tmp/brain/RFW_Web_Handoff_20261026/RFW_Web_Handoff_20261026');O=Path('/tmp/rfw-scenes');O.mkdir(parents=True,exist_ok=True);sid=sys.argv[-1]
manifest=json.loads((P/'assets/final/manifest.json').read_text())['assets'];v=next(s for s in json.loads((P/'handoff/website_content.json').read_text())['scenes'] if s['scene_id']==sid)['variants'][0]
bpy.ops.wm.open_mainfile(filepath=str(P/v['source_blend']));s=bpy.context.scene;s.frame_set(240 if sid=='space' else 1);cam=s.camera;startpos=cam.matrix_world.translation.copy();startrot=cam.matrix_world.to_quaternion().copy();deps=bpy.context.evaluated_depsgraph_get();out=[]
for a in manifest:
 if a['asset_id'] not in v['asset_ids']:continue
 prov=json.loads((P/a['provenance_file']).read_text());meshes=[bpy.data.objects[n] for n in prov['visual_mesh_objects']];pts=[o.evaluated_get(deps).matrix_world@Vector(b) for o in meshes for b in o.bound_box];lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)]);center=(lo+hi)/2
 xy=[world_to_camera_view(s,cam,p) for p in pts];screen=world_to_camera_view(s,cam,center)
 parts={}
 for o in meshes:
  parent=o.parent
  while parent and parent.type=='MESH':parent=parent.parent
  key=o.parent_bone if o.parent_type=='BONE' else (parent.name if parent and parent.name!=a['root_object'] else a['root_object'])
  g=parts.setdefault(key,{'name':key,'meshes':[],'materials':set(),'points':[]})
  g['meshes'].append(o.name);g['materials'].update(m.name for m in o.data.materials if m);g['points'] += [o.evaluated_get(deps).matrix_world@Vector(b) for b in o.bound_box]
 for g in parts.values():
  pp=g.pop('points');g['materials']=sorted(g['materials']);g['bounds']=[[min(p[i] for p in pp) for i in range(3)],[max(p[i] for p in pp) for i in range(3)]];g['dimensions_m']=[g['bounds'][1][i]-g['bounds'][0][i] for i in range(3)]
 direction=(startpos-center).normalized();direction.z=max(.2,direction.z);direction.normalize();endpos=center+direction*max(hi-lo)*2.5;endrot=(center-endpos).to_track_quat('-Z','Y')
 out.append({'id':a['asset_id'],'scene':sid,'root':a['root_object'],'bounds':[list(lo),list(hi)],'center':list(center),'startPosition':list(startpos),'startRotation':list(startrot),'endPosition':list(endpos),'endRotation':list(endrot),'lens':35,'sourceFrames':[240 if sid=='space' else 1,359 if sid=='space' else 120],'screen':list(screen),'rect':[min(p.x for p in xy),min(1-p.y for p in xy),max(p.x for p in xy),max(1-p.y for p in xy)],'parts':list(parts.values())})
(O/(sid+'-expansion.json')).write_text(json.dumps(out,indent=2));print('PREPARED',sid,flush=True)
