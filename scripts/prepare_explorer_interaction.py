"""Prepare a switchable damped interaction fixture without changing source records.

Virtual joint damping is rated effort / rated speed. Reflected armature is 2% of
the child subtree mass (slide), or 2% mass * collision radius squared (hinge).
These are demo controls, not inferred dataset attributes. The browser can switch
them off to inspect source dynamics. Validate the actual fixture in MuJoCo.
"""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import json
import numpy as np
import mujoco

ROOT=Path(__file__).resolve().parents[1]
WORK=Path('/tmp/rfw-explorer')


def prepare(asset):
    path=ROOT/'public'/asset['details'];details=json.loads(path.read_text())
    model=mujoco.MjModel.from_xml_path(str(ROOT/'public'/asset['simulation']))
    controls=[]
    for joint in asset['joints']:
        jid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,joint['name'])
        dof=int(model.jnt_dofadr[jid]);body=int(model.jnt_bodyid[jid]);mass=max(float(model.body_subtreemass[body]),1e-5)
        geoms=np.where(model.geom_bodyid==body)[0]
        radius=max([float(model.geom_rbound[i]+np.linalg.norm(model.geom_pos[i])) for i in geoms]+[.001])
        slide=joint['type']=='prismatic'
        effort=joint['effort'] if joint['effort'] and joint['effort']>0 else mass*9.81*(1 if slide else radius)
        speed=joint['velocity'] if joint['velocity'] and joint['velocity']>0 else (.1 if slide else 2)
        damping=max(float(model.dof_damping[dof]),effort/speed)
        armature=max(float(model.dof_armature[dof]),.02*mass*(1 if slide else radius**2))
        controls.append(dict(name=joint['name'],damping=damping,armature=armature,effort=effort,speed=speed))
        model.dof_damping[dof]=damping;model.dof_armature[dof]=armature
    details['simulation']['interaction']=dict(default=True,
        description='Switchable virtual joint damping and reflected armature for interactive inspection; source properties are unchanged.',
        rule='damping ≥ rated effort / rated speed; armature = 2% child subtree mass (slide) or 2% mass × collision radius² (hinge)',joints=controls)
    path.write_text(json.dumps(details,separators=(',',':')))
    data=mujoco.MjData(model);mujoco.mj_step(model,data,nstep=500)
    speeds=[]
    for item in controls:
        jid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,item['name']);dof=model.jnt_dofadr[jid]
        speeds.append(abs(float(data.qvel[dof]))/item['speed'])
    return dict(id=asset['id'],time=float(data.time),warnings=[int(w.number) for w in data.warning],
                maxVelocity=float(np.max(np.abs(data.qvel))) if len(data.qvel) else 0,maxRatedSpeedRatio=max(speeds,default=0))


if __name__=='__main__':
    manifest=json.loads((ROOT/'public/data/explorer.json').read_text())
    with ProcessPoolExecutor(max_workers=6) as pool:results=list(pool.map(prepare,manifest['assets']))
    (WORK/'interaction-validation.json').write_text(json.dumps(results,indent=2))
    print('Fixture checks',len(results),'warnings',sum(any(r['warnings']) for r in results))
    print('Highest speeds',sorted(results,key=lambda r:r['maxRatedSpeedRatio'],reverse=True)[:8])
