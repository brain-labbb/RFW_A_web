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


def load_urdf(path, joint_values=None, handle=None):
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


def cabinet(handle=None, gold=False, q=.14):
    root, meshes, links = load_urdf(SOURCE / 'crown_molding/model.urdf', {'body_to_door': q}, handle)
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


def edits():
    right, up, _ = camera((1.5, -2.5, 1.6), scale=3.25)
    for i, spec in enumerate([
        {'edit': 'height', 'scale': (1, 1, 1.28)},
        {'edit': 'radius', 'scale': (1.3, 1.3, 1)},
        {'edit': 'handle', 'handle': 't_bar'},
        {'edit': 'material', 'gold': True},
    ]):
        root, meshes, _ = cabinet(handle=spec.get('handle'), gold=spec.get('gold', False))
        root.scale = spec.get('scale', (1, 1, 1))
        tile(root, meshes, -.69 if i % 2 == 0 else .69, .67 if i < 2 else -.67, right, up, fixed_scale=1.5)
        audit['edits'].append(spec)


def pose():
    with POSES.open() as f:
        for row in f:
            p = json.loads(row)
            if p['frame'] == 700:
                return p
    raise ValueError('Pose frame not found')


def robot_scene(deploy=False):
    p = pose()
    audit['pose_source'] = str(POSES)
    audit['pose_frame'] = 700
    for side, arm in p['arms'].items():
        joints = dict(zip(['joint' + str(i) for i in range(1, 7)], arm['joint_pos_rad']))
        joints.update(dict(zip(['gripper', 'gripper_joint1', 'gripper_joint2'], arm['gripper_joint_pos_m'])))
        root, meshes, links = load_urdf(ROBOT, joints)
        root.location = arm['root_pos_m']
        root.rotation_mode = 'QUATERNION'
        root.rotation_quaternion = Quaternion(arm['root_quat_wxyz'])
        bpy.context.view_layer.update()
        # The recording stores the measured rigid-body poses of all fingers.
        # Record FK consistency and use those measured poses for the gripper visuals.
        checks = {}
        for name, raw in arm['finger_poses'].items():
            checks[name] = (links[name].matrix_world.translation - Vector(raw[:3])).length
            links[name].matrix_world = Matrix.Translation(Vector(raw[:3])) @ Quaternion(raw[3:]).to_matrix().to_4x4()
            bpy.context.view_layer.update()
        audit['robot_pose_checks'][side] = checks
    root, meshes, _ = cabinet(gold=True, q=p['joints']['round_cabinet_crown_molding']['body_to_door'])
    raw = p['mechanism_roots']['round_cabinet_crown_molding']
    root.location, root.scale = raw[:3], (.66,) * 3
    root.rotation_mode = 'QUATERNION'
    root.rotation_quaternion = Quaternion(raw[3:])
    tabletop = material('Neutral workbench', (.73, .75, .77), roughness=.8)
    cube('Workbench', (.12, .035, .705), (1.04, .93, .07), tabletop, .009)
    # The training schematic uses a quiet spatial grid. Deployment keeps the
    # same asset/robot composition and a plain workbench: these are illustrations.
    if not deploy:
        grid = material('Simulation grid', (.43, .48, .51), roughness=.75)
        for i in range(-4, 6):
            x = i * .1
            if -.39 < x < .63:
                line('Grid X', [(x, -.425, .741), (x, .495, .741)], grid, .0007)
        for i in range(-4, 5):
            y = i * .1 + .035
            line('Grid Y', [(-.39, y, .741), (.63, y, .741)], grid, .0007)
    else:
        frame_mat = material('Workbench frame', (.055, .06, .065), metallic=.45)
        for x in (-.32, .56):
            for y in (-.36, .43):
                cube('Table support', (x, y, .56), (.035, .035, .27), frame_mat, .004)
    # Camera looks toward the cabinet opening (source +X, rotated to world -X).
    camera((-2.4, 2.0, 1.7), target=(.10, .02, .76), scale=1.6)
    audit['illustration_only'] = True
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
