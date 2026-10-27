"""Render native authored scenes with new web cameras; sources are never saved over."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector,Quaternion
P=Path('/tmp/brain/RFW_Web_Handoff_20261026/RFW_Web_Handoff_20261026');O=Path('/tmp/rfw-scenes');sid,idx,mode=sys.argv[sys.argv.index('--')+1:];shot=json.loads((Path(__file__).parent/'scene_shots.json').read_text())[sid][int(idx)];v=next(s for s in json.loads((P/'handoff/website_content.json').read_text())['scenes'] if s['scene_id']==sid)['variants'][0];bpy.ops.wm.open_mainfile(filepath=str(P/v['source_blend']));s=bpy.context.scene;s.frame_set(1);old=s.camera;startlens=old.data.lens
if sid=='space':
 sys.path.insert(0,str(Path(__file__).parent))
 from extend_space_stage import extend_space_stage
 audit=extend_space_stage();(O/'space-extension.json').write_text(json.dumps(audit,indent=2))
camdata=bpy.data.cameras.new('Web walkthrough');cam=bpy.data.objects.new('Web walkthrough',camdata);s.collection.objects.link(cam);s.camera=cam;cam.rotation_mode='QUATERNION';camdata.clip_start=.02;camdata.clip_end=10000
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
s.render.engine='CYCLES';s.cycles.device='GPU';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.use_persistent_data=True;s.render.resolution_x=960;s.render.resolution_y=540;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.fps=24;s.render.threads_mode='FIXED';s.render.threads=6
out=O/'final-frames'/shot['id'];out.mkdir(exist_ok=True,parents=True)
if shot.get('aimAt'):shot['endRotation']=list((Vector(shot['aimAt'])-Vector(shot['endPosition'])).to_track_quat('-Z','Y'))
target_names=[]
if shot.get('trackTarget'):
 assets=json.loads((P/'assets/final/manifest.json').read_text())['assets'];asset=next(a for a in assets if a['asset_id']==shot['id']);target_names=json.loads((P/asset['provenance_file']).read_text())['visual_mesh_objects']
frames=[0,42,119] if mode=='preview' else range(120)
for f in frames:
 dst=out/f'{f:04d}.png'
 if dst.exists() and mode!='preview':continue
 s.frame_set(round(shot['sourceFrames'][0]+f))
 if target_names:
  deps=bpy.context.evaluated_depsgraph_get();pts=[bpy.data.objects[n].evaluated_get(deps).matrix_world@Vector(v) for n in target_names for v in bpy.data.objects[n].bound_box];center=Vector([(min(p[i] for p in pts)+max(p[i] for p in pts))/2 for i in range(3)]);offset=Vector(shot['endPosition'])-Vector(shot['center']);end=center+offset;rotation=(center-end).to_track_quat('-Z','Y')
 else:end=Vector(shot['endPosition']);rotation=Quaternion(shot['endRotation'])
 t=min(1,f/36);t=t*t*(3-2*t);cam.location=Vector(shot['startPosition']).lerp(end,t);cam.rotation_quaternion=Quaternion(shot['startRotation']).slerp(rotation,t);camdata.lens=startlens+(shot['lens']-startlens)*t;s.render.filepath=str(dst);bpy.ops.render.render(write_still=True)
print('RENDERED',shot['id'],mode,flush=True)
