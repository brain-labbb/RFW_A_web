"""Expand only the render copy's environment; preserve native assets, rigging and lighting."""
import bpy,math,collections
from mathutils import Vector

def extend_space_stage():
 terrain=bpy.data.objects['Lunar_Mars_continuous_terrain'];mesh=terrain.data
 uses=collections.defaultdict(list)
 for p in mesh.polygons:
  for i,a in enumerate(p.vertices):
   b=p.vertices[(i+1)%len(p.vertices)];uses[tuple(sorted((a,b)))].append((a,b))
 edges=[v[0] for v in uses.values() if len(v)==1];ids=sorted({i for e in edges for i in e});lookup={v:i for i,v in enumerate(ids)};n=len(ids)
 # Each new inner vertex exactly meets the original terrain boundary.
 coords=[terrain.matrix_world@mesh.vertices[i].co for i in ids];cx=sum(v.x for v in coords)/n;cy=sum(v.y for v in coords)/n
 vertices=[]
 for scale in [1,1.25,2,4,10]:
  for v in coords:
   z=v.z if scale==1 else v.z/scale-1.4*math.log(scale)
   vertices.append((cx+(v.x-cx)*scale,cy+(v.y-cy)*scale,z))
 faces=[]
 for ring in range(4):
  for a,b in edges:
   i,j=lookup[a],lookup[b];faces.append((ring*n+j,ring*n+i,(ring+1)*n+i,(ring+1)*n+j))
 m=bpy.data.meshes.new('Web terrain continuation');m.from_pydata(vertices,[],faces);m.update();o=bpy.data.objects.new('Web terrain continuation',m);bpy.context.scene.collection.objects.link(o)
 for mat in terrain.data.materials:m.materials.append(mat)
 for p in m.polygons:p.use_smooth=True
 # The native star material is retained on a camera-visible dome, with the Earth kept separate.
 old=bpy.data.objects['TEASER_navy_twilight_backdrop'];mat=old.data.materials[0].copy();mat.name='Web panoramic native stars';old.hide_render=True
 nodes=mat.node_tree.nodes;links=mat.node_tree.links;uv=next(n for n in nodes if n.type=='TEX_COORD');split=next(l.to_node for l in links if l.from_node==uv and l.to_node.type=='SEPXYZ')
 mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY_ADD';mapping.inputs[1].default_value=(1,4,1);mapping.inputs[2].default_value=(0,-1.45,0);links.new(uv.outputs['UV'],mapping.inputs[0]);links.new(mapping.outputs['Vector'],split.inputs[0])
 bpy.ops.mesh.primitive_uv_sphere_add(segments=128,ring_count=64,radius=4000,location=(0,0,0));sky=bpy.context.object;sky.name='Web panoramic star dome';sky.data.materials.append(mat)
 for p in sky.data.polygons:p.use_smooth=True
 for prop in ['visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow']:setattr(sky,prop,False)
 return {'terrain_boundary_vertices':n,'extension_vertices':len(vertices),'sky_radius':4000,'earth_preserved':True}
