"""Export audited native assets and authored animation. Run with Blender 5.2+."""
import bpy,json,sys,pathlib,time
args=sys.argv[sys.argv.index('--')+1:]
root=pathlib.Path(args[0]); dest=pathlib.Path(args[1]); only=args[2:]
manifest=json.loads((root/'assets/final/manifest.json').read_text())
dest.mkdir(parents=True,exist_ok=True)
for asset in manifest['assets']:
 aid=asset['asset_id']
 if only and aid not in only: continue
 if (dest/(aid+'.glb')).exists(): continue
 try:
  bpy.ops.wm.open_mainfile(filepath=str(root/asset['blend_file']))
  scene=bpy.context.scene;scene.frame_set(1)
  for im in bpy.data.images:
   if im.size[0]>1024 or im.size[1]>1024:
    scale=1024/max(im.size);im.scale(max(1,int(im.size[0]*scale)),max(1,int(im.size[1]*scale)))
  bpy.ops.export_scene.gltf(filepath=str(dest/(aid+'.glb')),export_format='GLB',export_extras=False,
   export_animations=True,export_animation_mode='SCENE',export_anim_scene_split_object=False,
   export_frame_range=True,export_frame_step=6,export_bake_animation=True,
   export_force_sampling=True,export_anim_slide_to_zero=True,export_cameras=False,export_lights=False)
  print('EXPORTED',aid,flush=True)
 except Exception as e:
  print('FAILED',aid,repr(e),flush=True)
