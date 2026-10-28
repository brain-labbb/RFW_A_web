"""Validate published explorer models and run one-second source-pose rollouts."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import struct
import xml.etree.ElementTree as ET
import numpy as np
import mujoco

ROOT=Path(__file__).resolve().parents[1]
WORK=Path('/tmp/rfw-explorer')


def check(asset):
    for key in ['image','model','details','simulation']:
        assert (ROOT/'public'/asset[key]).is_file(), (asset['id'],key)
    source=WORK/'source'/asset['sourceRelative']/'model.urdf'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==asset['urdfHash']
    blob=(ROOT/'public'/asset['model']).read_bytes()
    gltf=json.loads(blob[20:20+struct.unpack_from('<I',blob,12)[0]])
    links={n.get('extras',{}).get('rfw_link') for n in gltf['nodes'] if n.get('extras',{}).get('rfw_link')}
    surfaces={n.get('extras',{}).get('rfw_surface') for n in gltf['nodes'] if n.get('extras',{}).get('rfw_surface')}
    path=ROOT/'public'/asset['details'];details=json.loads(path.read_text())
    assert links=={p['name'] for p in details['links']}
    assert surfaces=={p['id'] for p in details['parts']}
    model=mujoco.MjModel.from_xml_path(str(ROOT/'public'/asset['simulation']))
    assert model.njnt==len(asset['joints'])
    for joint in asset['joints']:
        assert mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,joint['name'])>=0
    derived=[]
    for link in details['links']:
        if link['massKg'] is None:
            i=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,link['name'])
            derived.append(dict(link=link['name'],massKg=float(model.body_mass[i]),principalInertia=model.body_inertia[i].tolist(),source='MuJoCo geometry-derived default'))
    details['simulation']['derivedInertials']=derived
    if derived:
        details['simulation']['inertia']='Source URDF inertials where recorded; missing link inertials use MuJoCo geometry-derived defaults (density 1000 kg/m³)'
    path.write_text(json.dumps(details,separators=(',',':')))
    data=mujoco.MjData(model)
    mujoco.mj_step(model,data,nstep=500)
    assert np.isfinite(data.qpos).all()
    warnings=[int(w.number) for w in data.warning]
    result=dict(id=asset['id'],links=len(links),surfaces=len(surfaces),joints=model.njnt,collisionShapes=model.ngeom,
                time=float(data.time),warnings=warnings,maxVelocity=float(np.max(np.abs(data.qvel))) if len(data.qvel) else 0,
                derivedInertials=derived)
    return result


if __name__=='__main__':
    manifest=json.loads((ROOT/'public/data/explorer.json').read_text())
    assert len(manifest['families'])==30 and len(manifest['assets'])==180
    by_id={a['id']:a for a in manifest['assets']}
    excluded=json.loads((ROOT/'scripts/explorer_exclusions.json').read_text())
    assert not (set(by_id) & set(excluded['samples']))
    assert not ({a['category'] for a in manifest['assets']} & set(excluded['categories']))
    for family in manifest['families']:
        assert len(family['samples'])==6
        expected=set(family.get('templateHashes',{}).values()) or {family['templateHash']}
        assert {by_id[i]['templateHash'] for i in family['samples']}==expected
        assert family['inputs']
        for item in family['inputs']:assert (ROOT/'public'/item['image']).is_file()
    with ProcessPoolExecutor(max_workers=6) as pool:results=list(pool.map(check,manifest['assets']))
    (WORK/'source-validation.json').write_text(json.dumps(results,indent=2))
    print('Validated',len(results),'source rigs, geometry IDs, assets and physics exports.')
    warning_cases=[r for r in results if any(r['warnings']) or r['time']<.99]
    print('Rollouts with warnings:',len(warning_cases),[(r['id'],r['warnings'],r['time']) for r in warning_cases])
