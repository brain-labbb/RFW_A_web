import loadMujoco from '@mujoco/mujoco';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';

const root = new URL('../public/', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('data/explorer.json', root)));
const mj = await loadMujoco();
const results = [];
for (const asset of manifest.assets) {
  let model, data;
  try {
    const info = JSON.parse(await readFile(new URL(asset.details, root)));
    model = mj.MjModel.from_xml_string(await readFile(new URL(asset.simulation, root), 'utf8'));
    assert.equal(info.simulation.collisionFilter.version, 'adjacent-rigid-groups-v1');
    const joints = info.simulation.interaction.joints.map(j => {
      const id = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT.value, j.name);
      assert.ok(id >= 0);
      const dof = model.jnt_dofadr[id];
      model.dof_damping[dof] = j.damping; model.dof_armature[dof] = j.armature;
      return {...j, dof};
    });
    data = new mj.MjData(model);
    let peakRatio = 0;
    for (let step = 0; step < 5000; step++) {
      mj.mj_step(model, data);
      assert.ok(data.qpos.every(Number.isFinite) && data.qvel.every(Number.isFinite), 'nonfinite state');
      for (const j of joints) peakRatio = Math.max(peakRatio, Math.abs(data.qvel[j.dof]) / j.speed);
      assert.ok(peakRatio <= 10, `speed guard triggered (${peakRatio.toFixed(3)}×)`);
    }
    assert.ok(data.time > 9.999, 'engine reset during rollout');
    results.push({id: asset.id, time: data.time, peakRatio});
  } catch (error) {
    results.push({id: asset.id, error: error.message});
    console.log('FAIL', asset.id, error.message);
  } finally { data?.delete(); model?.delete(); }
  if (results.length % 20 === 0) console.log('Checked', results.length, '/', manifest.assets.length);
}
await mkdir('/tmp/rfw-explorer', {recursive:true});
await writeFile('/tmp/rfw-explorer/wasm-interaction-validation.json', JSON.stringify(results, null, 2));
const failures = results.filter(r => r.error);
console.log('WASM 10-second default-pose checks:', results.length, 'failures:', failures.length);
process.exitCode = failures.length ? 1 : 0;
