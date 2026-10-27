"""Render four workflow panels from native RFW-A / dual-Piper assets.

Blender 4.2 (Collada importer required). Example:
CUDA_VISIBLE_DEVICES=0 blender -b -t 8 --python scripts/render_robotics_workflow.py -- retrieve
All source assets are read-only; intermediate images/scenes/audits go to /tmp.
The edit panel shows native experiment assets in an illustrative arrangement.
The deployment panel is a schematic, not a photograph of a trial.
"""
import argparse
import hashlib
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
USD_SOURCE = Path('/opt/isaacsim/isaac_route/assets/articulated/generated')
MATERIAL_REPORT = Path('/opt/isaacsim/end/viewpoint_match_20261013/round_cabinet/material_import_report.json')
MATERIAL_RECORDS = {r['stem']: r for r in json.loads(MATERIAL_REPORT.read_text())}
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
    m.diffuse_color = (*color[:3], 1)
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


def load_urdf(path, joint_values=None):
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
TRAY = material('Visible matte gray trays', (.30, .33, .35), roughness=.85)
SELECTED_TRAY = material('Selected blue gray tray', (.10, .23, .29), roughness=.75)
EDGE = material('Selected asset', (.018, .095, .14), roughness=1)
edge_shader = EDGE.node_tree.nodes.new('ShaderNodeEmission')
edge_shader.inputs['Color'].default_value = (.018, .095, .14, 1)
EDGE.node_tree.links.new(edge_shader.outputs[0], EDGE.node_tree.nodes.get('Material Output').inputs['Surface'])


def cabinet(variant='crown_molding', q=.98):
    """Import the exact composed visual USD used to render the experiment video.

    USD import retains the fixed PBR textures, metric UVs and per-part bindings.
    MAKE_UNIQUE prevents identically named materials in different assets from
    being accidentally reused. Physics/collision geometry is invisible in USD.
    """
    stem = 'round_cabinet_' + variant
    source = USD_SOURCE / (stem + '.usd')
    record = MATERIAL_RECORDS[stem]
    before = set(bpy.data.objects)
    bpy.ops.wm.usd_import(filepath=str(source), import_visible_only=True,
                          import_materials=True, mtl_name_collision_mode='MAKE_UNIQUE')
    imported = set(bpy.data.objects) - before
    root = empty(stem)
    for ob in imported:
        if ob.parent not in imported:
            ob.parent = root
    door = next(o for o in imported if o.name.split('.')[0] == 'curved_door')
    door.matrix_basis = door.matrix_basis @ Matrix.Rotation(q, 4, 'Z')
    meshes = [o for o in imported if o.type == 'MESH']
    bound_surfaces = set()
    texture_paths = set()
    for ob in meshes:
        matches = [re.search(r'original_pbr_(\d+)', m.name) for m in ob.data.materials]
        if not matches or any(m is None for m in matches):
            raise ValueError('Unexpected unmapped/collision geometry: ' + ob.name)
        surface = record['surfaces'][int(matches[0][1])]
        ob['link_name'], ob['visual_name'] = surface.split('::', 1)
        ob['workflow_cabinet'] = stem
        bound_surfaces.add(surface)
        for mat in ob.data.materials:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    path = Path(bpy.path.abspath(node.image.filepath)).resolve()
                    if not path.is_file():
                        raise FileNotFoundError(path)
                    texture_paths.add(path)
    if bound_surfaces != set(record['surfaces']):
        raise ValueError('USD surface bindings do not match the video material report')
    audit['sources'] += [str(source), record['appearance_layer'], str(MATERIAL_REPORT)]
    audit.setdefault('video_asset_imports', []).append({
        'stem': stem, 'source': str(source), 'appearance_layer': record['appearance_layer'],
        'surfaces': sorted(bound_surfaces), 'door_angle_rad': q,
        'textures': [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(texture_paths)],
    })
    if variant == 'crown_molding':
        # Color-managed Blender reproduction of the delivered Isaac appearance:
        # preserve the source USD on disk; compensate for different lighting and
        # display pipelines only in this illustration's imported coating shader.
        for mat in {m for ob in meshes for m in ob.data.materials}:
            bs = mat.node_tree.nodes.get('Principled BSDF')
            if bs and bs.inputs['Base Color'].default_value[0] > .1:
                bs.inputs['Base Color'].default_value = (.27, .265, .085, 1)
        audit['yellow_display_calibration'] = {
            'source_linear_rgb': [.23, .19, .045],
            'blender_linear_rgb': [.27, .265, .085],
            'reference': 'delivered sim_crown_molding.mp4; appearance match, not a new material',
        }
    bpy.context.view_layer.update()
    return root, meshes, {'curved_door': door}


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
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=radius, depth=.034, location=(cx, cy, lo.z - .018))
    bpy.context.object.data.materials.append(SELECTED_TRAY if selected else TRAY)
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
        line('Selected candidate', [forward + right*x + up*y for x, y in points], EDGE, .013)


def edits():
    audit['presentation_door_angle_rad'] = .98
    right, up, _ = camera((1.5, -2.5, 1.6), scale=3.25)
    variants = [('seed_0000', 'light wood'), ('seed_0001', 'light wood'),
                ('strap_loop', 'light wood'), ('crown_molding', 'yellow coating'),
                ('seed_0001', 'dark walnut'), ('t_bar', 'blue gray coating')]
    for i, (variant, finish) in enumerate(variants):
        root, meshes, _ = cabinet(variant)
        body = [o for o in meshes if o.get('visual_name') in
                ('shell', 'plinth', 'foot_ring', 'shelf_post', 'door_panel')]
        if finish == 'blue gray coating':
            mat = material('Illustrative blue gray coating', (.045, .10, .135), metallic=.12, roughness=.38)
            for ob in body:
                ob.data.materials.clear()
                ob.data.materials.append(mat)
        elif finish == 'dark walnut':
            # Tint the native wood texture, retaining its actual UVs and grain.
            for mat in {m for o in body for m in o.data.materials}:
                bs = mat.node_tree.nodes.get('Principled BSDF')
                socket = bs.inputs['Base Color']
                tint = mat.node_tree.nodes.new('ShaderNodeMixRGB')
                tint.blend_type = 'MULTIPLY'
                tint.inputs[0].default_value = 1
                tint.inputs[2].default_value = (.20, .075, .028, 1)
                if socket.is_linked:
                    source = socket.links[0].from_socket
                    mat.node_tree.links.new(source, tint.inputs[1])
                else:
                    tint.inputs[1].default_value = socket.default_value
                mat.node_tree.links.new(tint.outputs[0], socket)
        tile(root, meshes, (i % 3 - 1) * 1.02, .66 if i < 3 else -.66,
             right, up, fixed_scale=1.12)
        audit['edits'].append({'native_asset': 'round_cabinet_' + variant,
                               'finish': finish, 'illustration_only': True})
    audit['edit_layout'] = '2 rows by 3 columns; six method examples, not six recorded trials'


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
    height_scale = .72 if deploy else 1.0
    source_xml = ET.parse(SOURCE / 'crown_molding/model.urdf').getroot()
    knob_origin = source_xml.find("link[@name='curved_door']/visual[@name='knob_cap']/origin")
    handle_height = vec(knob_origin.get('xyz'))[2]
    arm_offset = .66 * handle_height * (height_scale - 1)
    hardware_rgb = (.006, .008, .011) if deploy else (.035, .075, .12)
    hardware = material('Dark physical hardware' if deploy else 'Blue simulation hardware', hardware_rgb, .12, .45)
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
        if deploy and side == active_side:
            root.location.z += arm_offset
            bpy.context.view_layer.update()
        for ob in meshes:
            # Only the working arm is needed in the close-up. The second arm's
            # recorded pose is still audited, but its idle gripper is hidden.
            ob.data.materials.clear()
            ob.data.materials.append(hardware)
            ob.hide_render = side != active_side or (deploy and ob.get('link_name') in ('base_link', 'link1', 'link2'))
    root, meshes, _ = cabinet(q=p['joints']['round_cabinet_crown_molding']['body_to_door'])
    raw = p['mechanism_roots']['round_cabinet_crown_molding']
    root.location, root.scale = raw[:3], (.66, .66, .66 * height_scale)
    root.rotation_mode = 'QUATERNION'
    root.rotation_quaternion = Quaternion(raw[3:])
    bpy.context.view_layer.update()
    if deploy:
        for ob in meshes:
            if ob.get('visual_name', '').startswith(('knob_', 'tbar_')):
                # Lower hardware with the shortened body but retain its original
                # dimensions, rather than squashing the round knob vertically.
                matrix = ob.matrix_world.copy()
                for j in range(3):
                    matrix[2][j] /= height_scale
                ob.matrix_world = matrix
        bpy.context.view_layer.update()
    # Simulation grid and blue mesh overlay are schematic visual cues.
    # Deployment keeps a plain background and soft contact shadow.
    if deploy:
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, .737))
        floor = bpy.context.object
        floor.name = 'Invisible deployment shadow catcher'
        floor.is_shadow_catcher = True
        floor.data.materials.append(WHITE)
    else:
        grid = material('Blue simulation grid', (.025, .09, .18), roughness=1)
        shader = grid.node_tree.nodes.new('ShaderNodeEmission')
        shader.inputs['Color'].default_value = (.035, .12, .23, 1)
        grid.node_tree.links.new(shader.outputs[0], grid.node_tree.nodes.get('Material Output').inputs['Surface'])
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, .736))
        bpy.context.object.name = 'Simulation ground, no tabletop'
        bpy.context.object.data.materials.append(material('Cool simulation ground', (.46, .55, .63), roughness=.9))
        for i in range(-20, 21):
            v = i * .05
            line('Simulation grid X', [(v, -1, .738), (v, 1, .738)], grid, .00065)
            line('Simulation grid Y', [(-1, v, .738), (1, v, .738)], grid, .00065)
        for ob in list(bpy.context.scene.objects):
            if ob.type == 'MESH' and ob.get('link_name') and not ob.get('workflow_cabinet') and not ob.hide_render:
                overlay = ob.copy()
                overlay.data = ob.data.copy()
                bpy.context.collection.objects.link(overlay)
                overlay.name = 'Simulation topology ' + ob.name
                overlay.data.materials.clear()
                overlay.data.materials.append(grid)
                dec = overlay.modifiers.new('Readable topology', 'DECIMATE')
                dec.ratio = .06
                wire = overlay.modifiers.new('Blue mesh edges', 'WIREFRAME')
                wire.thickness = .00035
                wire.use_even_offset = False
                wire.use_relative_offset = False
                wire.offset = 1
    motion_arrow(raw[:3], opening=not deploy)
    camera((-3.0, 2.0, 2.5) if deploy else (-3.0, -.9, 1.8),
           target=(.30, .025, .90 if deploy else .945), scale=.70)
    audit['tabletop'] = False
    audit['contact_shadow'] = deploy
    audit['illustration_only'] = True
    audit['cabinet_finish'] = 'native video USD materials with documented Blender display calibration'
    audit['simulation_grid'] = not deploy
    audit['cabinet_height_scale'] = height_scale
    audit['active_arm_presentation_translation_m'] = [0, 0, arm_offset]
    audit['presentation_style'] = 'physical deployment schematic' if deploy else 'shaded simulation schematic'
    audit['robot_finish'] = 'darker physical schematic' if deploy else 'blue simulation mesh schematic'
    audit['robot_material_source'] = '/opt/isaacsim/piper_official_isaac_asset_20260827/isaac_usd/piper.usd'
    audit['robot_diffuse_linear_rgb'] = list(hardware_rgb)
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
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (1.0, 1.0, 1.0, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = 1.0
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
scene.view_settings.view_transform = 'Khronos PBR Neutral'
scene.view_settings.exposure = .1
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = str(OUT / (args.panel + '.png'))
audit['render'] = {'blender': bpy.app.version_string, 'engine': scene.render.engine, 'samples': scene.cycles.samples, 'view_transform': scene.view_settings.view_transform, 'exposure': scene.view_settings.exposure, 'devices': [d.name for d in prefs.devices if d.use]}
(OUT / (args.panel + '.json')).write_text(json.dumps(audit, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (args.panel + '.blend')))
bpy.ops.render.render(write_still=True)
