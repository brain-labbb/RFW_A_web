"""Convert source URDF dynamics/collision geometry to self-contained browser MJCF.

This is a fixed-base articulated interaction demo. Concave source collision meshes
use CoACD decomposition; convex meshes keep their hull. Source link
inertials, joint limits, damping, friction loss and mimic constraints are retained.
No annotations are guessed from mesh ordering.
"""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import mujoco
import coacd
from explorer_collision import add_adjacent_exclusions
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
WORK = Path('/tmp/rfw-explorer')
COLLISION_VERSION = 'CoACD convex decomposition of concave source collision meshes (relative tolerance 0.03–0.05)'


def fmt(values):
    return ' '.join(f'{v:.9g}' for v in values)


def origin(element):
    if element is None:
        return dict(pos='0 0 0', quat='1 0 0 0')
    angles = [float(x) for x in element.get('rpy','0 0 0').split()]
    q = Rotation.from_euler('xyz', angles).as_quat()
    return dict(pos=element.get('xyz','0 0 0'), quat=fmt([q[3],*q[:3]]))


def convert(a):
    directory = WORK/'source'/a['sourceRelative']
    source = ET.parse(directory/'model.urdf').getroot()
    model = ET.Element('mujoco', model=a['id'])
    ET.SubElement(model,'compiler', angle='radian', autolimits='true', fusestatic='false')
    ET.SubElement(model,'option', timestep='0.002', integrator='implicitfast', gravity='0 0 -9.81', iterations='50')
    assets = ET.SubElement(model,'asset')
    world = ET.SubElement(model,'worldbody')
    defaults=ET.SubElement(model,'default')
    ET.SubElement(defaults,'geom', solref='0.01 1', solimp='0.9 0.95 0.001')
    links={l.get('name'):l for l in source.findall('link')}
    children={}
    childnames=set()
    for joint in source.findall('joint'):
        children.setdefault(joint.find('parent').get('link'),[]).append(joint)
        childnames.add(joint.find('child').get('link'))
    adjustments=[]
    collision_repairs=[]
    mesh_cache={}
    def body(name,parent,joint=None):
        link=links[name]
        b=ET.SubElement(parent,'body',name=name,**origin(joint.find('origin') if joint is not None else None))
        inertial=link.find('inertial')
        if inertial is not None:
            mass=float(inertial.find('mass').get('value'))
            it=inertial.find('inertia')
            tensor=np.array([[float(it.get('ixx')),float(it.get('ixy','0')),float(it.get('ixz','0'))],
                             [float(it.get('ixy','0')),float(it.get('iyy')),float(it.get('iyz','0'))],
                             [float(it.get('ixz','0')),float(it.get('iyz','0')),float(it.get('izz'))]])
            io=inertial.find('origin')
            rpy=[float(x) for x in (io.get('rpy','0 0 0') if io is not None else '0 0 0').split()]
            rotation=Rotation.from_euler('xyz',rpy).as_matrix()
            tensor=rotation@tensor@rotation.T
            values,vectors=np.linalg.eigh(tensor)
            if mass<=0:
                raise ValueError(f'{name}: nonpositive source mass')
            if min(values)<=0:
                before=values.copy();values=np.maximum(values,max(values[-1]*1e-6,1e-12))
                tensor=vectors@np.diag(values)@vectors.T
                adjustments.append(dict(link=name,kind='inertia_positive_projection',before=before.tolist(),after=values.tolist()))
            # Roundoff in tiny source inertias can violate the triangle inequality.
            if values[2]>values[0]+values[1]:
                before=values.copy();values[2]=(values[0]+values[1])*.999999
                tensor=vectors@np.diag(values)@vectors.T
                adjustments.append(dict(link=name,kind='inertia_triangle_projection',before=before.tolist(),after=values.tolist()))
            ET.SubElement(b,'inertial',mass=str(mass),pos=io.get('xyz','0 0 0') if io is not None else '0 0 0',
                          fullinertia=fmt([tensor[0,0],tensor[1,1],tensor[2,2],tensor[0,1],tensor[0,2],tensor[1,2]]))
        if joint is not None and joint.get('type')!='fixed':
            kind=joint.get('type')
            axis=joint.find('axis');limit=joint.find('limit');dynamics=joint.find('dynamics')
            attrs=dict(name=joint.get('name'),type='slide' if kind=='prismatic' else 'hinge',axis=axis.get('xyz','1 0 0') if axis is not None else '1 0 0')
            if kind!='continuous' and limit is not None:
                lower=float(limit.get('lower','0'));upper=float(limit.get('upper','0'))
                if upper>lower:attrs['range']=fmt([lower,upper])
            if dynamics is not None:
                if dynamics.get('damping') is not None:attrs['damping']=dynamics.get('damping')
                if dynamics.get('friction') is not None:attrs['frictionloss']=dynamics.get('friction')
            ET.SubElement(b,'joint',**attrs)
        for i,c in enumerate(link.findall('collision')):
            geometry=c.find('geometry');attrs=dict(name=f'{name}__collision_{i}',**origin(c.find('origin')))
            friction=c.find('gazebo/mu1')
            if friction is not None:attrs['friction']=f'{float(friction.text)} 0.005 0.0001'
            mesh=geometry.find('mesh');box=geometry.find('box');cylinder=geometry.find('cylinder');sphere=geometry.find('sphere')
            if mesh is not None:
                path=directory/mesh.get('filename');scale=mesh.get('scale','1 1 1')
                key=hashlib.sha256(path.read_bytes()+scale.encode()).hexdigest()
                if key not in mesh_cache:
                    loaded=trimesh.load(path,force='mesh',process=True)
                    loaded.apply_scale(np.array([float(x) for x in scale.split()]))
                    hull=loaded.convex_hull
                    cache=WORK/'collision-cache'/f'{key}.json'
                    cache.parent.mkdir(exist_ok=True)
                    if cache.exists():
                        chunks=json.loads(cache.read_text())
                    elif abs(loaded.volume) < hull.volume*.97 and len(loaded.faces)>12:
                        if loaded.volume<0:loaded.invert()
                        coacd.set_log_level('error')
                        pieces=coacd.run_coacd(coacd.Mesh(loaded.vertices,loaded.faces),threshold=.05,resolution=1000,
                            mcts_iterations=10,mcts_nodes=8,mcts_max_depth=2,preprocess_resolution=30,max_convex_hull=24,decimate=True,max_ch_vertex=64)
                        chunks=[dict(vertices=v.tolist(),faces=f.tolist()) for v,f in pieces]
                        temporary=cache.with_suffix(f'.{os.getpid()}.tmp');temporary.write_text(json.dumps(chunks));temporary.replace(cache)
                    else:
                        chunks=[dict(vertices=hull.vertices.tolist(),faces=hull.faces.tolist())]
                        temporary=cache.with_suffix(f'.{os.getpid()}.tmp');temporary.write_text(json.dumps(chunks));temporary.replace(cache)
                    usable=[]
                    for chunk in chunks:
                        vertices=np.array(chunk['vertices'])
                        fragment_volume=abs(trimesh.Trimesh(vertices=vertices,faces=chunk['faces'],process=False).volume)
                        if len(vertices)<4 or np.linalg.matrix_rank(vertices-vertices.mean(axis=0),tol=1e-10)<3 or fragment_volume<max(1e-12,hull.volume*1e-8):
                            collision_repairs.append(dict(link=name,collision=c.get('name'),kind='omit_degenerate_decomposition_fragment',volume=float(fragment_volume)))
                            continue
                        usable.append(chunk)
                    if not usable:
                        usable=[dict(vertices=hull.vertices.tolist(),faces=hull.faces.tolist())]
                        collision_repairs.append(dict(link=name,collision=c.get('name'),kind='source_convex_hull_fallback'))
                    mesh_cache[key]=[]
                    for piece_index,chunk in enumerate(usable):
                        mesh_name=f'm{len(mesh_cache)}_{piece_index}';mesh_cache[key].append(mesh_name)
                        ET.SubElement(assets,'mesh',name=mesh_name,vertex=fmt(np.array(chunk['vertices']).reshape(-1)),face=' '.join(map(str,np.array(chunk['faces']).reshape(-1))))
                for piece_index,mesh_name in enumerate(mesh_cache[key]):
                    ET.SubElement(b,'geom',**{**attrs,'name':attrs['name']+f'_{piece_index}','type':'mesh','mesh':mesh_name})
                continue
            elif box is not None:attrs.update(type='box',size=fmt(np.array([float(x) for x in box.get('size').split()])/2))
            elif cylinder is not None:attrs.update(type='cylinder',size=fmt([float(cylinder.get('radius')),float(cylinder.get('length'))/2]))
            elif sphere is not None:attrs.update(type='sphere',size=sphere.get('radius'))
            else:raise ValueError('Unsupported collision geometry')
            ET.SubElement(b,'geom',**attrs)
        for child in children.get(name,[]):body(child.find('child').get('link'),b,child)
    for name in links:
        if name not in childnames:body(name,world)
    equality=ET.SubElement(model,'equality')
    for joint in source.findall('joint'):
        mimic=joint.find('mimic')
        if mimic is not None:
            ET.SubElement(equality,'joint',joint1=joint.get('name'),joint2=mimic.get('joint'),
                          polycoef=f"{mimic.get('offset','0')} {mimic.get('multiplier','1')} 0 0 0")
    text=ET.tostring(model,encoding='unicode')
    compiled=mujoco.MjModel.from_xml_string(text)
    collision_filter=add_adjacent_exclusions(model,compiled)
    text=ET.tostring(model,encoding='unicode')
    compiled=mujoco.MjModel.from_xml_string(text)
    data=mujoco.MjData(compiled)
    for _ in range(50):mujoco.mj_step(compiled,data)
    if not np.all(np.isfinite(data.qpos)):raise ValueError('Nonfinite smoke rollout')
    out=ROOT/'public'/a['simulation'];temporary=out.with_suffix(f'.{os.getpid()}.tmp');temporary.write_text(text);temporary.replace(out)
    details_path=ROOT/'public'/a['details'];details=json.loads(details_path.read_text())
    details['simulation']=dict(engine='MuJoCo',base='fixed',collision=COLLISION_VERSION,collisionFilter=collision_filter,
        inertia='Source URDF link inertials; missing inertials use geometry-derived defaults (density 1000 kg/m³)',adjustments=adjustments,collisionRepairs=collision_repairs,
        friction='Source URDF mu1 as sliding friction; torsional 0.005, rolling 0.0001',
        contact='MuJoCo soft contacts (solref 0.01 1); source restitution is displayed, not converted',
        material='Rigid bodies; Young’s modulus and Poisson ratio are annotations, not soft-body parameters')
    temporary=details_path.with_suffix(f'.{os.getpid()}.tmp');temporary.write_text(json.dumps(details,separators=(',',':')));temporary.replace(details_path)
    return dict(id=a['id'],bodies=compiled.nbody,joints=compiled.njnt,geoms=compiled.ngeom,
                adjustments=adjustments,smokeTime=float(data.time),bytes=out.stat().st_size)


def attempt(asset):
    try:
        return convert(asset)
    except Exception as error:
        return dict(id=asset['id'],error=str(error))


if __name__=='__main__':
    manifest=json.loads((WORK/'selection-progress.json').read_text())
    todo=[a for a in manifest['assets'] if not (ROOT/'public'/a['simulation']).exists() or json.loads((ROOT/'public'/a['details']).read_text()).get('simulation',{}).get('collision') != COLLISION_VERSION]
    if len(sys.argv)>1:todo=[a for a in todo if a['id'] in sys.argv[1:]]
    with ProcessPoolExecutor(max_workers=8) as pool:
        results=[]
        for result in pool.map(attempt,todo):
            results.append(result)
            print('FAILED' if 'error' in result else 'READY',result['id'],result.get('error',str(result.get('geoms'))+' collision shapes'),flush=True)
    (WORK/'physics-export.json').write_text(json.dumps(results,indent=2))
    print('Compiled and stepped',len(results),'source models',flush=True)
    if any('error' in r for r in results):
        raise SystemExit('Some source models failed; see physics-export.json')
