"""Match source annotation groups by their scaled centroid and solid volume.

VLM part names are often descriptive rather than URDF names. Matching is accepted
only when both geometric signatures agree, with a unique set of source surfaces.
Repeated surfaces can share an annotation; their annotation mass is never summed.
Writes an audit under /tmp; --apply updates the website details after exports end.
"""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict
import json
import re
import sys
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[1]
WORK=Path('/tmp/rfw-explorer')
OUT=WORK/'property-matches';OUT.mkdir(exist_ok=True)


def transform(node):
    matrix=np.eye(4)
    if node is not None:
        matrix[:3,:3]=Rotation.from_euler('xyz',[float(x) for x in node.get('rpy','0 0 0').split()]).as_matrix()
        matrix[:3,3]=[float(x) for x in node.get('xyz','0 0 0').split()]
    return matrix


def match(asset):
    source=WORK/'source'/asset['sourceRelative']
    data=json.loads((source/'part_physics.json').read_text())
    annotation=json.loads((source/'affordance/affordance_annot.json').read_text())['affordances']
    tree=ET.parse(source/'model.urdf').getroot()
    parents={j.find('child').get('link'):(j.find('parent').get('link'),transform(j.find('origin'))) for j in tree.findall('joint')}
    world={}
    def frame(name):
        if name not in world:world[name]=frame(parents[name][0])@parents[name][1] if name in parents else np.eye(4)
        return world[name]
    surfaces=[];groups=defaultdict(list)
    for link in tree.findall('link'):
        name=link.get('name')
        for visual in link.findall('visual'):
            vname=visual.get('name','');geom=visual.find('geometry');mesh=geom.find('mesh')
            matrix=frame(name)@transform(visual.find('origin'));center=np.zeros(3);volume=0
            if mesh is not None:
                shape=trimesh.load(source/mesh.get('filename'),force='mesh',process=False)
                shape.apply_scale([float(x) for x in mesh.get('scale','1 1 1').split()])
                volume=abs(shape.volume);center=shape.center_mass
            elif geom.find('box') is not None:volume=np.prod([float(x) for x in geom.find('box').get('size').split()])
            elif geom.find('cylinder') is not None:
                c=geom.find('cylinder');volume=np.pi*float(c.get('radius'))**2*float(c.get('length'))
            elif geom.find('sphere') is not None:volume=4/3*np.pi*float(geom.find('sphere').get('radius'))**3
            center=(matrix@np.r_[center,1])[:3];center=center[[0,2,1]]*np.array([1,1,-1])*data['scale']
            volume*=data['scale']**3
            surface=dict(id=name+'::'+vname,volume=volume,center=center)
            index=len(surfaces);surfaces.append(surface)
            base=re.sub(r'\d+','',vname).strip('_')
            groups[(name,base)].append(index);groups[('*',base)].append(index)
    candidates={tuple([i]) for i in range(len(surfaces))}
    candidates.update(tuple(indices) for indices in groups.values() if len(indices)>1)
    signatures=[]
    for indices in candidates:
        volume=sum(surfaces[i]['volume'] for i in indices)
        if volume<=0:continue
        center=sum(surfaces[i]['center']*surfaces[i]['volume'] for i in indices)/volume
        signatures.append((indices,volume,center))
    tolerance=max(1.2e-5,np.linalg.norm(data.get('real_bbox',[1,1,1]))*2e-4)
    matches=[]
    for a in annotation:
        physics=data['parts'].get(str(a['id']))
        if not physics or not physics.get('volume_m3') or not physics.get('centroid'):continue
        expected_volume=physics['volume_m3'];expected_center=np.array(physics['centroid'])
        accepted=[];centroid_matches=[]
        for indices,volume,center in signatures:
            error=abs(volume-expected_volume)/expected_volume
            if np.linalg.norm(center-expected_center)<tolerance:
                centroid_matches.append(indices)
                if error<.025:accepted.append(indices)
        method='scaled centroid and volume'
        estimator=physics.get('volume_estimator','')
        if not accepted and len(centroid_matches)==1 and any(tag in estimator for tag in ['thinwall','voxel','convex']):
            accepted=centroid_matches;method='unique scaled centroid (source volume uses '+estimator+')'
        if len(accepted)==1:
            matches.append(dict(annotationId=a['id'],surfaces=[surfaces[i]['id'] for i in accepted[0]],method=method))
    result=dict(id=asset['id'],matches=matches,surfaces=len(surfaces),annotations=len(annotation))
    (OUT/f"{asset['id']}.json").write_text(json.dumps(result))
    return result


if __name__=='__main__':
    manifest=json.loads((ROOT/'public/data/explorer.json').read_text())
    if '--apply' in sys.argv:
        total=0
        for asset in manifest['assets']:
            report=json.loads((OUT/f"{asset['id']}.json").read_text())
            path=ROOT/'public'/asset['details'];data=json.loads(path.read_text())
            raw=json.loads((WORK/'source'/asset['sourceRelative']/'part_physics.json').read_text())
            anns={a['id']:a for a in data['sourceAnnotations']}
            mapping=defaultdict(list)
            for match in report['matches']:
                for surface in match['surfaces']:mapping[surface].append(match)
            for part in data['parts']:
                if len(mapping[part['id']])!=1:continue
                match=mapping[part['id']][0];a=anns[match['annotationId']]
                part.update(annotationId=a['id'],physics=raw['parts'][str(a['id'])],description=a.get('Basic_description',''),function=a.get('Functional_description',''),
                            annotationMapping=dict(method=match['method'],sharedSurfaces=match['surfaces']))
                total+=1
            path.write_text(json.dumps(data,separators=(',',':')))
        print('Geometry-verified annotations for',total,'surfaces')
    else:
        with ProcessPoolExecutor(max_workers=8) as pool:results=list(pool.map(match,manifest['assets']))
        print('Matched',sum(sum(len(m['surfaces']) for m in r['matches']) for r in results),'of',sum(r['surfaces'] for r in results),'surfaces')
