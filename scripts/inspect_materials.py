import bpy,json,pathlib,sys
from mathutils import Vector
root=pathlib.Path(sys.argv[-2]);output=pathlib.Path(sys.argv[-1]); all_assets=[]
for a in json.loads((root/'assets/final/manifest.json').read_text())['assets']:
 bpy.ops.wm.open_mainfile(filepath=str(root/a['blend_file']));bpy.context.scene.frame_set(1)
 surfaces=[];all_points=[]
 for o in bpy.context.scene.objects:
  if o.type!='MESH':continue
  points=[o.matrix_world@Vector(v) for v in o.bound_box];all_points+=points
  mats=[]
  for m in o.data.materials:
   if not m:continue
   values={'name':m.name,'base_color':list(m.diffuse_color)}
   if m.use_nodes:
    for n in m.node_tree.nodes:
     if n.type=='BSDF_PRINCIPLED':
      for k in ['Base Color','Metallic','Roughness','Transmission Weight']:
       if k in n.inputs:
        v=n.inputs[k].default_value;values[k]=list(v) if hasattr(v,'__len__') else v
   mats.append(values)
  surfaces.append({'name':o.name,'materials':mats})
 dimensions=[max(p[i] for p in all_points)-min(p[i] for p in all_points) for i in range(3)]
 all_assets.append({'id':a['asset_id'],'label':a['label'],'dimensions_m':dimensions,'surfaces':surfaces})
output.write_text(json.dumps(all_assets))
