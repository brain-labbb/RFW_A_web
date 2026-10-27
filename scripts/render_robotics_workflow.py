"""Render four workflow panels from native RFW-A / dual-Piper assets.

Blender 4.2 (Collada importer required). Example:
CUDA_VISIBLE_DEVICES=0 blender -b -t 8 --python scripts/render_robotics_workflow.py -- retrieve
All source assets are read-only; intermediate images/scenes/audits go to /tmp.
The edit panel illustrates controlled transforms of one source asset, not a new
experiment. The deployment panel is a schematic, not a photograph of a trial.
"""
import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Euler, Quaternion

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/opt/isaacsim/sim_asset/round_cabinet')
ROBOT = Path('/opt/isaacsim/piper_official_isaac_asset_20260827/official_source/piper_with_gripper.urdf')
POSES = Path('/opt/isaacsim/end/real_sim_fixed_camera_20261014/round_cabinet/round_cabinet_fixed_camera.jsonl')
OUT = Path('/tmp/rfw-workflow')
OUT.mkdir(exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument('panel', choices=['retrieve', 'edit', 'train', 'deploy'])
parser.add_argument('--preview', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
bpy.ops.wm.read_factory_settings(use_empty=True)
audit = {'panel': args.panel, 'sources': [], 'edits': [], 'robot_pose_checks': {}}


def vec(s, default='0 0 0'):
    return tuple(map(float, (s or default).split()))


def origin(el):
    if el is None:
        return Matrix.Identity(4)
    return Matrix.Translation(vec(el.get('xyz'))) @ Euler(vec(el.get('rpy')), 'XYZ').to_matrix().to_4x4()


def empty(name, parent=None, matrix=None):
    ob = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(ob)
    ob.parent = parent
    if matrix is not None:
        ob.matrix_basis = matrix
    return ob


def material(name, color, metallic=0, roughness=.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color[:3], 1)
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = roughness
    return m


def srgb(rgb):
    return tuple(c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb[:3])


MATS = {}

def urdf_material(path, link, visual):
    """Use original URDF material colors; robot DAE materials are imported intact."""
    key = (str(path), link, visual.get('name'))
    if key in MATS:
        return MATS[key]
    vm = visual.find('material')
    col = vm.find('color') if vm is not None else None
    rgb = vec(col.get('rgba'))[:3] if col is not None else (.18, .18, .18)
    m = material('source_' + str(len(MATS)), srgb(rgb))
    bs = m.node_tree.nodes.get('Principled BSDF')
    # The original URDF colors are the coherent source material palette.
    # Some adjacent appearance.json texture references are incomplete; do not
    # invent replacements or silently substitute unrelated material-library maps.
    if vm is not None and 'metal' in vm.get('name', ''):
        bs.inputs['Metallic'].default_value = .65
        bs.inputs['Roughness'].default_value = .3
    MATS[key] = m
    return m


def load_urdf(path, joint_values=None, handle=None, interior=None):
    joint_values = joint_values or {}
    xml = ET.parse(path).getroot()
    root = empty(path.parent.name)
    links = {l.get('name'): empty(l.get('name'), root) for l in xml.findall('link')}
    for joint in xml.findall('joint'):
        child = links[joint.find('child').get('link')]
        child.parent = links[joint.find('parent').get('link')]
        axis_el = joint.find('axis')
        axis = Vector(vec(axis_el.get('xyz') if axis_el is not None else '1 0 0'))
        q = joint_values.get(joint.get('name'), 0)
        motion = Matrix.Identity(4)
        if joint.get('type') in ('revolute', 'continuous'):
            motion = Matrix.Rotation(q, 4, axis)
        elif joint.get('type') == 'prismatic':
            motion = Matrix.Translation(axis * q)
        child.matrix_basis = origin(joint.find('origin')) @ motion
    meshes = []
    for link in xml.findall('link'):
        visuals = [(v, path) for v in link.findall('visual')]
        if interior and link.get('name') == 'cabinet_body':
            ip = SOURCE / interior / 'model.urdf'
            ix = ET.parse(ip).getroot()
            shelf = ix.find("link[@name='cabinet_body']/visual[@name='shelf_post']")
            if shelf is None:
                raise ValueError('Native shelf unit missing: ' + str(ip))
            visuals.append((shelf, ip))
            audit['sources'].append(str(ip))
        if handle and link.get('name') == 'curved_door':
            visuals = [(v, p) for v, p in visuals if not v.get('name', '').startswith('knob_')]
            hp = SOURCE / handle / 'model.urdf'
            hx = ET.parse(hp).getroot()
            handles = [v for v in hx.findall("link[@name='curved_door']/visual") if v.get('name', '').startswith(('tbar_', 'handle_'))]
            if handle == 't_bar':
                # Regenerate the two native cylindrical components using the
                # updated generator's exposed dimensions, translated to this
                # cabinet's radius (0.210 vs the donor's 0.185 metres).
                source = (hp.parent / 'model.py').read_text()
                def param(name):
                    return float(re.search(r'^' + name + r' = ([0-9.]+)', source, re.M)[1])
                for v in handles:
                    stem = v.get('name') == 'tbar_stem'
                    r = param('TBAR_STEM_R_MID' if stem else 'TBAR_TIP_R') + .025
                    v.find('origin').set('xyz', f'{r*math.cos(math.radians(-52))} {r*math.sin(math.radians(-52))} 0.289')
                    c = v.find('geometry/cylinder')
                    c.set('radius', str(param('TBAR_STEM_RADIUS' if stem else 'TBAR_BAR_RADIUS')))
                    c.set('length', str(param('TBAR_STEM_LENGTH' if stem else 'TBAR_BAR_LENGTH')))
                audit['edits'].append({'handle_source': str(hp.parent / 'model.py'), 'radial_offset_m': .025})
            visuals += [(v, hp) for v in handles]
            audit['sources'].append(str(hp))
        for visual, vp in visuals:
            geom = visual.find('geometry')
            mesh, box, cyl, sphere = (geom.find(k) for k in ('mesh', 'box', 'cylinder', 'sphere'))
            before = set(bpy.data.objects)
            collada = False
            if mesh is not None:
                mp = vp.parent / mesh.get('filename')
                if mp.suffix == '.obj':
                    bpy.ops.wm.obj_import(filepath=str(mp), forward_axis='Y', up_axis='Z')
                elif mp.suffix == '.stl':
                    bpy.ops.wm.stl_import(filepath=str(mp))
                elif mp.suffix == '.dae':
                    bpy.ops.wm.collada_import(filepath=str(mp))
                    collada = True
                else:
                    raise ValueError(mp)
            elif box is not None:
                bpy.ops.mesh.primitive_cube_add(size=1)
            elif cyl is not None:
                bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=float(cyl.get('radius')), depth=float(cyl.get('length')))
            elif sphere is not None:
                bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=float(sphere.get('radius')))
            else:
                raise ValueError(ET.tostring(geom))
            new = set(bpy.data.objects) - before
            anchor = empty(link.get('name') + '::' + visual.get('name', 'mesh'), links[link.get('name')], origin(visual.find('origin')))
            if box is not None:
                anchor.scale = vec(box.get('size'))
            elif mesh is not None:
                anchor.scale = vec(mesh.get('scale'), '1 1 1')
            for ob in new:
                if ob.parent not in new:
                    # Preserve imported Collada node transforms, including detailed mesh materials.
                    matrix = ob.matrix_world.copy() if collada else Matrix.Identity(4)
                    ob.parent = anchor
                    ob.matrix_basis = matrix
                if ob.type != 'MESH':
                    continue
                ob['visual_name'] = visual.get('name', '')
                ob['link_name'] = link.get('name')
                if not collada:
                    ob.data.materials.clear()
                    ob.data.materials.append(urdf_material(vp, link.get('name'), visual))
                if not ob.data.uv_layers and not collada:
                    bpy.ops.object.select_all(action='DESELECT')
                    ob.select_set(True)
                    bpy.context.view_layer.objects.active = ob
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.uv.cube_project(cube_size=1)
                    bpy.ops.object.mode_set(mode='OBJECT')
                meshes.append(ob)
    audit['sources'].append(str(path))
    bpy.context.view_layer.update()
    return root, meshes, links


def bounds(meshes):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def cube(name, loc, size, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(mat)
    if bevel:
        mod = ob.modifiers.new('Soft edges', 'BEVEL')
        mod.width, mod.segments = bevel, 3
        ob.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return ob


def line(name, points, mat, radius=.008):
    cr = bpy.data.curves.new(name, 'CURVE')
    cr.dimensions = '3D'
    cr.bevel_depth = radius
    cr.bevel_resolution = 3
    sp = cr.splines.new('POLY')
    sp.points.add(len(points) - 1)
    for p, v in zip(sp.points, points):
        p.co = (*v, 1)
    ob = bpy.data.objects.new(name, cr)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def camera(direction, target=(0, 0, 0), scale=3.65):
    target = Vector(target)
    cam = bpy.data.cameras.new('Orthographic camera')
    ob = bpy.data.objects.new('Camera', cam)
    bpy.context.collection.objects.link(ob)
    ob.location = target + Vector(direction).normalized() * 10
    ob.rotation_euler = (target - ob.location).to_track_quat('-Z', 'Y').to_euler()
    cam.type, cam.ortho_scale = 'ORTHO', scale
    bpy.context.scene.camera = ob
    rotation = ob.rotation_euler.to_matrix()
    return rotation @ Vector((1, 0, 0)), rotation @ Vector((0, 1, 0)), ob


WHITE = material('Porcelain', (.91, .92, .93), roughness=.72)
EDGE = material('Selected asset', (.28, .36, .35), roughness=.6)
GOLD = material('Recorded cabinet appearance', (.23, .19, .045), roughness=.85)


def cabinet(handle=None, gold=False, q=.98, interior=None):
    root, meshes, links = load_urdf(SOURCE / 'crown_molding/model.urdf', {'body_to_door': q}, handle, interior)
    if gold:
        for ob in meshes:
            if ob['visual_name'] in ('shell', 'door_panel', 'plinth', 'crown_molding', 'base_molding'):
                ob.data.materials.clear()
                ob.data.materials.append(GOLD)
    return root, meshes, links


def tile(root, meshes, sx, sy, right, up, size=.8, fixed_scale=None, selected=False):
    lo, hi = bounds(meshes)
    scale = size / max(hi - lo) if fixed_scale is None else fixed_scale
    root.scale = [s * scale for s in root.scale]
    lo, hi = bounds(meshes)
    center = (lo + hi) / 2
    center_target = right * sx + up * sy
    root.location += center_target - center
    bpy.context.view_layer.update()
    lo, hi = bounds(meshes)
    # A small local plinth catches light under each item without a busy background.
    cx, cy = ((lo + hi) / 2)[:2]
    radius = max(hi.x - lo.x, hi.y - lo.y) * .62
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=radius, depth=.018, location=(cx, cy, lo.z - .014))
    bpy.context.object.data.materials.append(WHITE)
    if selected:
        pts = [(cx + radius * math.cos(i * 2 * math.pi / 128), cy + radius * math.sin(i * 2 * math.pi / 128), lo.z) for i in range(129)]
        line('Retrieved cabinet highlight', pts, EDGE, .014)


def retrieval():
    audit['presentation_door_angle_rad'] = .98
    right, up, cam = camera((1.5, -2.5, 1.6), scale=3.5)
    ids = [
        'satellite_with_articulated_solar_panels__0000',
        'Handtools_Paint_roller__0000',
        'Astronomy_Mars_rover__0000',
        'drawer_cabinet_with_sliding_drawers__0000',
        None,
        'Healthcare_Prosthetic_limb__0000',
        'sewing_machine__0000',
        'Playground_swing__0000',
        'Industrial_Drill_press_table__0000',
    ]
    for i, name in enumerate(ids):
        if name is None:
            root, meshes, _ = cabinet()
        else:
            p = ROOT / 'public/models/dataset' / (name + '.glb')
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=str(p))
            new = set(bpy.data.objects) - before
            root = empty(name)
            for ob in new:
                if ob.parent not in new:
                    ob.parent = root
            meshes = [o for o in new if o.type == 'MESH']
            audit['sources'].append(str(p.relative_to(ROOT)))
        tile(root, meshes, (i % 3 - 1) * 1.1, (1 - i // 3) * 1.05, right, up, size=.86 if name is None else .73, selected=name is None)

    # Render the retrieval selection brackets in the camera plane. There is
    # exactly one selected candidate in a mixed-category pool.
    forward = cam.location.normalized() * 2
    for xsign, ysign in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        points = [(xsign * .48, ysign * .38), (xsign * .48, ysign * .52), (xsign * .34, ysign * .52)]
        line('Selected candidate', [forward + right*x + up*y for x, y in points], EDGE, .008)


FINISHES = {
    'walnut': ((.15, .073, .034), (.065, .029, .014), .38, 0),
    'blue_gray': ((.065, .155, .175), (.040, .085, .095), .40, .22),
}


def finish_cabinet(meshes, finish):
    if finish == 'target':
        body = trim = GOLD
    else:
        color, trim_color, roughness, metallic = FINISHES[finish]
        body = material(finish + ' body', color, metallic, roughness)
        trim = material(finish + ' trim', trim_color, metallic, roughness)
        if finish == 'walnut':
            # A restrained procedural wood finish is part of this illustration's
            # material edit, not an asserted dataset texture assignment.
            nodes, links = body.node_tree.nodes, body.node_tree.links
            tex = nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value = 3
            mapping = nodes.new('ShaderNodeVectorMath');mapping.operation = 'MULTIPLY'
            mapping.inputs[1].default_value = (7, 7, .65)
            coord = nodes.new('ShaderNodeTexCoord')
            links.new(coord.outputs['Generated'], mapping.inputs[0])
            links.new(mapping.outputs[0], tex.inputs['Vector'])
            ramp = nodes.new('ShaderNodeValToRGB')
            ramp.color_ramp.elements[0].color = (.09, .039, .016, 1)
            ramp.color_ramp.elements[1].color = (.20, .105, .049, 1)
            links.new(tex.outputs['Fac'], ramp.inputs[0])
            links.new(ramp.outputs[0], nodes.get('Principled BSDF').inputs['Base Color'])
    hardware = material(finish + ' hardware', (.25, .15, .055), .7, .28) if finish == 'blue_gray' else None
    for ob in meshes:
        name = ob.get('visual_name', '')
        replacement = body if name in ('shell', 'door_panel', 'shelf_post') else trim if name in ('plinth', 'crown_molding', 'base_molding') else hardware if name.startswith(('knob_', 'tbar_')) else None
        if replacement:
            ob.data.materials.clear();ob.data.materials.append(replacement)


def edits():
    audit['presentation_door_angle_rad'] = .98
    right, up, _ = camera((1.5, -2.5, 1.6), scale=3.25)
    for i, spec in enumerate([
        {'finish': 'walnut', 'scale': (.96, .96, 1.22), 'handle': 't_bar', 'interior': 'seed_0000'},
        {'finish': 'walnut', 'scale': (1.25, 1.25, .93)},
        {'finish': 'blue_gray', 'scale': (1, 1, 1)},
        {'finish': 'target', 'scale': (1.08, 1.08, 1.06), 'handle': 't_bar'},
    ]):
        root, meshes, _ = cabinet(handle=spec.get('handle'), interior=spec.get('interior'))
        finish_cabinet(meshes, spec['finish'])
        root.scale = spec['scale']
        tile(root, meshes, -.69 if i % 2 == 0 else .69, .67 if i < 2 else -.67, right, up, fixed_scale=1.5)
        audit['edits'].append(spec)


def pose(frame):
    with POSES.open() as f:
        for row in f:
            p = json.loads(row)
            if p['frame'] == frame:
                return p
    raise ValueError('Pose frame not found')


def motion_arrow(center, opening=True):
    """A 3D arc around the actual vertical door axis, with a tangent arrowhead."""
    start, end = ((2.35, 3.95) if opening else (3.95, 2.35))
    radius = .196
    points = [Vector((center[0] + radius*math.cos(t), center[1] + radius*math.sin(t), .785))
              for t in [start + (end-start)*i/64 for i in range(65)]]
    ink = material('Door motion arrow', (.01, .05, .06), roughness=1)
    shader = ink.node_tree.nodes.new('ShaderNodeEmission')
    shader.inputs['Color'].default_value = (.025, .09, .105, 1)
    ink.node_tree.links.new(shader.outputs[0], ink.node_tree.nodes.get('Material Output').inputs['Surface'])
    line('Door motion arc', points, ink, .0038)
    tangent = (points[-1]-points[-2]).normalized()
    length = .032
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=.012, radius2=0, depth=length, location=points[-1]+tangent*length/2)
    ob = bpy.context.object
    ob.name = 'Door motion arrowhead'
    ob.rotation_euler = tangent.to_track_quat('Z', 'Y').to_euler()
    ob.data.materials.append(ink)


def robot_scene(deploy=False):
    frame = 1800 if deploy else 900
    p = pose(frame)
    active_side = 'right' if deploy else 'left'
    audit['pose_source'] = str(POSES)
    audit['pose_frame'] = frame
    audit['visible_arm'] = active_side
    audit['motion_phase'] = 'closing' if deploy else 'opening'
    graphite = material('Deployment hardware finish', (.025, .031, .035), .3, .37)
    for side, arm in p['arms'].items():
        joints = dict(zip(['joint' + str(i) for i in range(1, 7)], arm['joint_pos_rad']))
        joints.update(dict(zip(['gripper', 'gripper_joint1', 'gripper_joint2'], arm['gripper_joint_pos_m'])))
        root, meshes, links = load_urdf(ROBOT, joints)
        root.location = arm['root_pos_m']
        root.rotation_mode = 'QUATERNION'
        root.rotation_quaternion = Quaternion(arm['root_quat_wxyz'])
        bpy.context.view_layer.update()
        checks = {}
        for name, raw in arm['finger_poses'].items():
            checks[name] = (links[name].matrix_world.translation - Vector(raw[:3])).length
            links[name].matrix_world = Matrix.Translation(Vector(raw[:3])) @ Quaternion(raw[3:]).to_matrix().to_4x4()
            bpy.context.view_layer.update()
        audit['robot_pose_checks'][side] = checks
        for ob in meshes:
            # Only the working arm is needed in the close-up. The second arm's
            # recorded pose is still audited, but its idle gripper is hidden.
            ob.hide_render = side != active_side or (deploy and ob.get('link_name') in ('base_link', 'link1', 'link2'))
            if deploy:
                ob.data.materials.clear();ob.data.materials.append(graphite)
    root, meshes, _ = cabinet(q=p['joints']['round_cabinet_crown_molding']['body_to_door'])
    finish_cabinet(meshes, 'target' if deploy else 'blue_gray')
    raw = p['mechanism_roots']['round_cabinet_crown_molding']
    root.location, root.scale = raw[:3], (.66,) * 3
    root.rotation_mode = 'QUATERNION'
    root.rotation_quaternion = Quaternion(raw[3:])
    # Contact shadows ground the close-up, without a large table or legs that
    # compete with the action. No source geometry or recorded pose is altered.
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, .737))
    floor = bpy.context.object;floor.name = 'Contact shadow plane'
    floor.is_shadow_catcher = True;floor.data.materials.append(WHITE)
    if not deploy:
        grid = material('Simulation grid', (.26, .33, .36), roughness=.9)
        for i in range(-3, 5):
            x = .347+i*.08
            line('Grid X', [(x, -.23, .738), (x, .30, .738)], grid, .00065)
        for i in range(-3, 4):
            y = .034+i*.08
            line('Grid Y', [(.08, y, .738), (.64, y, .738)], grid, .00065)
    motion_arrow(raw[:3], opening=not deploy)
    camera((-3.0, 2.0, 1.8) if deploy else (-3.0, -.9, 1.8), target=(.30, .025, .945), scale=.70)
    audit['illustration_only'] = True
    audit['cabinet_finish'] = 'target' if deploy else 'blue_gray'
    audit['robot_finish'] = 'graphite presentation finish' if deploy else 'original Collada materials'
    audit['target_material_source'] = '/opt/isaacsim/isaac_route/assets/articulated/generated/round_cabinet_crown_molding_appearance.usda'



{'retrieve': retrieval, 'edit': edits, 'train': lambda: robot_scene(False), 'deploy': lambda: robot_scene(True)}[args.panel]()
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24 if args.preview else 128
scene.cycles.use_denoising = True
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type == 'OPTIX'
scene.cycles.device = 'GPU'
scene.world = bpy.data.worlds.new('Soft studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.82, .86, .90, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .65
robot = args.panel in ('train', 'deploy')
center = Vector((.1, .02, 1.0) if robot else (0, 0, 0))
scale = .6 if robot else 1.5
for name, direction, power in [('Key', (1, -3, 5), 350), ('Fill', (-4, -1, 3), 230), ('Rim', (2, 4, 3), 280)]:
    light = bpy.data.lights.new(name, 'AREA')
    light.energy, light.size = power * scale * scale, 3.5 * scale
    ob = bpy.data.objects.new(name, light)
    bpy.context.collection.objects.link(ob)
    ob.location = center + Vector(direction) * scale
    ob.rotation_euler = (center - ob.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.resolution_x = 720 if args.preview else 1280
scene.render.resolution_y = scene.render.resolution_x
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.view_settings.view_transform = 'AgX'
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = str(OUT / (args.panel + '.png'))
audit['render'] = {'blender': bpy.app.version_string, 'samples': scene.cycles.samples, 'devices': [d.name for d in prefs.devices if d.use]}
(OUT / (args.panel + '.json')).write_text(json.dumps(audit, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (args.panel + '.blend')))
bpy.ops.render.render(write_still=True)
