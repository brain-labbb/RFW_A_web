"""Blender 5.2: import a curated URDF slice with source PBR bindings; export static rig + previews.
The scene assets are untouched. Sample geometry remains in source units. No generated motion is
claimed as simulation: browser sliders apply the original URDF joint transforms.
"""
import bpy,sys,json,math,xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Matrix,Vector,Euler
ROOT=Path(__file__).resolve().parents[1];SRC=Path('/data/oss_bucket_0/yuanbo/PV_A_vlm/assets');TMP=Path('/tmp/rfw-dataset');TMP.mkdir(exist_ok=True)
data=json.loads((ROOT/'public/data/dataset.json').read_text());MODELS=ROOT/'public/models/dataset';MODELS.mkdir(parents=True,exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
def xyz(text,default='0 0 0'):return tuple(map(float,(text or default).split()))
def origin(el):
 if el is None:return Matrix.Identity(4)
 return Matrix.Translation(xyz(el.get('xyz')))@Euler(xyz(el.get('rpy')),'XYZ').to_matrix().to_4x4()
def empty(name,parent=None,matrix=None):
 o=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(o);o.parent=parent
 if matrix is not None:o.matrix_basis=matrix
 return o

def build(a):
 bpy.ops.wm.read_factory_settings(use_empty=True)
 p=SRC/a['sourceRelative'];xml=ET.parse(p/'model.urdf').getroot();app=json.loads((p/'appearance.json').read_text());bindings={b['surface_key']:b for b in app['bindings']};materials={};missing=[]
 global_colors={m.get('name'):xyz(m.find('color').get('rgba'),'0.6 0.6 0.6 1') for m in xml.findall('material') if m.find('color') is not None}
 def material(link,v):
  key=link+'::'+v.get('name','');binding=bindings.get(key,{});appearance=binding.get('appearance') or {};channels=appearance.get('channels') or {};tag=(binding.get('material') or {}).get('material_id') or key
  if tag in materials:return materials[tag]
  m=bpy.data.materials.new('surface_'+str(len(materials)));m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');vm=v.find('material');rgba=(.6,.6,.6,1)
  if vm is not None:
   col=vm.find('color');rgba=xyz(col.get('rgba'),'0.6 0.6 0.6 1') if col is not None else global_colors.get(vm.get('name'),rgba)
  # URDF colors are display RGB; convert them for Blender's linear shader.
  bs.inputs['Base Color'].default_value=tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgba[:3])+(rgba[3],)
  bs.inputs['Roughness'].default_value=.5
  for chan,socket in [('base_color','Base Color'),('roughness','Roughness'),('metallic','Metallic'),('transmission','Transmission Weight'),('ior','IOR'),('alpha','Alpha')]:
   c=channels.get(chan)
   if not c:continue
   if c.get('kind')=='factor' and 'value' in c:
    bs.inputs[socket].default_value=c['value'];continue
   if c.get('kind')!='texture':continue
   path=p/c['path']
   if not path.exists():missing.append(c['path']);continue
   tex=m.node_tree.nodes.new('ShaderNodeTexImage');im=bpy.data.images.load(str(path),check_existing=True)
   if max(im.size)>512:im.scale(512,512)
   if chan!='base_color':im.colorspace_settings.name='Non-Color'
   tex.image=im;m.node_tree.links.new(tex.outputs['Color'],bs.inputs[socket])
  materials[tag]=m;return m
 links={l.get('name'):empty(l.get('name')) for l in xml.findall('link')}
 for j in xml.findall('joint'):
  par=links[j.find('parent').get('link')];child=links[j.find('child').get('link')]
  anchor=empty('joint_origin_'+j.get('name'),par,origin(j.find('origin')))
  motion=empty('joint_motion_'+j.get('name'),anchor);child.parent=motion
  axis=j.find('axis');limit=j.find('limit')
  if j.get('type')!='fixed':
   motion['rfw_joint']=j.get('name');motion['rfw_type']=j.get('type');motion['rfw_axis']=xyz(axis.get('xyz') if axis is not None else '1 0 0');motion['rfw_lower']=float(limit.get('lower','0')) if limit is not None else 0;motion['rfw_upper']=float(limit.get('upper','0')) if limit is not None else 0
 meshes=[]
 for l in xml.findall('link'):
  for v in l.findall('visual'):
   g=v.find('geometry');before=set(bpy.data.objects);mesh=g.find('mesh');box=g.find('box');cyl=g.find('cylinder');sphere=g.find('sphere')
   if mesh is not None:
    path=p/mesh.get('filename');ext=path.suffix.lower()
    if ext=='.obj':bpy.ops.wm.obj_import(filepath=str(path),forward_axis='Y',up_axis='Z')
    elif ext=='.stl':bpy.ops.wm.stl_import(filepath=str(path))
    else:raise ValueError('Unsupported mesh '+str(path))
   elif box is not None:bpy.ops.mesh.primitive_cube_add(size=1)
   elif cyl is not None:bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=float(cyl.get('radius')),depth=float(cyl.get('length')))
   elif sphere is not None:bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=float(sphere.get('radius')))
   else:raise ValueError('Unsupported geometry')
   objects=[o for o in set(bpy.data.objects)-before if o.type=='MESH']
   for o in objects:
    o.name=l.get('name')+'::'+v.get('name','surface');o.parent=links[l.get('name')];o.matrix_basis=origin(v.find('origin'))
    if box is not None:o.scale=xyz(box.get('size'))
    elif mesh is not None:o.scale=xyz(mesh.get('scale'),'1 1 1')
    o.data.materials.clear();o.data.materials.append(material(l.get('name'),v));o['rfw_part']=l.get('name');o['rfw_material_class']=bindings.get(o.name,{}).get('material_class_id') or ''
    if not o.data.uv_layers:
     bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.cube_project(cube_size=1);bpy.ops.object.mode_set(mode='OBJECT')
    meshes.append(o)
 bpy.context.view_layer.update()
 # Root transform maps source Z-up to glTF Y-up; original mesh and joint transforms stay intact.
 bpy.ops.export_scene.gltf(filepath=str(MODELS/(a['id']+'.glb')),export_format='GLB',export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='JPEG',export_jpeg_quality=80)
 render(a,meshes,missing,bindings)

def render(a,meshes,missing,bindings):
 points=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box];lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)]);center=(lo+hi)/2;r=max(hi-lo)
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
 try:
  prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='CUDA';prefs.get_devices()
  for d in prefs.devices:d.use=d.type=='CUDA'
  scene.cycles.device='GPU'
 except Exception:pass
 scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.75,.78,.75,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
 bpy.ops.mesh.primitive_plane_add(size=r*200,location=(center.x,center.y,lo.z-r*.015));floor=bpy.context.object;m=bpy.data.materials.new('Backdrop');m.diffuse_color=(.89,.91,.89,1);floor.data.materials.append(m)
 for label,offset,power in [('Key',(2,-3,4),420),('Fill',(-3,-1,2),200),('Rim',(1,3,3),300)]:
  ld=bpy.data.lights.new(label,'AREA');ld.energy=power*r*r;ld.shape='DISK';ld.size=r*3;o=bpy.data.objects.new(label,ld);scene.collection.objects.link(o);o.location=center+Vector(offset)*r;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
 cam=bpy.data.cameras.new('Camera');o=bpy.data.objects.new('Camera',cam);scene.collection.objects.link(o)
 direction=(1.5,-2,1.1)
 if a['category']=='ceiling_fan':direction=(1.3,-2,-.9)
 o.location=center+Vector(direction)*r; o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=r*2.0;scene.camera=o
 # Fan camera looks up at a ceiling fixture: move floor below view.
 if a['category']=='ceiling_fan':floor.hide_render=True
 scene.render.resolution_x=640;scene.render.resolution_y=480;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(TMP/(a['id']+'.png'));scene.render.film_transparent=False
 bpy.ops.render.render(write_still=True)
 (TMP/(a['id']+'.audit.json')).write_text(json.dumps({'id':a['id'],'bounds':[list(lo),list(hi)],'mesh_objects':len(meshes),'missing_textures':missing,'material_bindings':len(bindings)},indent=2))
 print('READY',a['id'],flush=True)
for a in data['assets']:
 if args and args[0]!='render-only' and a['id'] not in args:continue
 if args and args[0]=='render-only':
  bpy.ops.wm.read_factory_settings(use_empty=True)
  bpy.ops.import_scene.gltf(filepath=str(MODELS/(a['id']+'.glb')))
  # Blender's glTF importer already converts Y-up back to Blender Z-up.
  root=empty('Preview root')
  for o in list(bpy.context.scene.objects):
   if o!=root and o.parent is None:o.parent=root
  bpy.context.view_layer.update()
  audit=json.loads((TMP/(a['id']+'.audit.json')).read_text())
  render(a,[o for o in bpy.context.scene.objects if o.type=='MESH'],audit['missing_textures'],range(a['sourceBindings']))
  continue
 if (TMP/(a['id']+'.audit.json')).exists():continue
 try:build(a)
 except Exception as e:print('FAILED',a['id'],repr(e),flush=True);raise
