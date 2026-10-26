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
frames=[0,42,119] if mode=='preview' else range(120)
for f in frames:
 dst=out/f'{f:04d}.png'
 if dst.exists() and mode!='preview':continue
 s.frame_set(round(shot['sourceFrames'][0]+f));t=min(1,f/36);t=t*t*(3-2*t);cam.location=Vector(shot['startPosition']).lerp(Vector(shot['endPosition']),t);cam.rotation_quaternion=Quaternion(shot['startRotation']).slerp(Quaternion(shot['endRotation']),t);camdata.lens=startlens+(shot['lens']-startlens)*t;s.render.filepath=str(dst);bpy.ops.render.render(write_still=True)
print('RENDERED',shot['id'],mode,flush=True)
