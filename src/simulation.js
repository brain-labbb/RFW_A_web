import loadMujoco from '@mujoco/mujoco';
import wasmUrl from '@mujoco/mujoco/mujoco.wasm?url';

let modulePromise;
export async function loadSimulation(xml, joints, interaction) {
  modulePromise ??= loadMujoco({locateFile: path => path.endsWith('.wasm') ? wasmUrl : path}).catch(error => {
    modulePromise = null;
    throw error;
  });
  const mj = await modulePromise;
  const model = mj.MjModel.from_xml_string(xml);
  let data;
  try { data = new mj.MjData(model); } catch (error) { model.delete(); throw error; }
  const mapping = joints.map(joint => {
    const id = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT.value, joint.name);
    if (id < 0) throw Error(`Simulation joint missing: ${joint.name}`);
    return {...joint, qpos: model.jnt_qposadr[id], dof: model.jnt_dofadr[id]};
  });
  let accumulator = 0, impulse = null, disposed = false;
  const originalDamping = model.dof_damping.slice(), originalArmature = model.dof_armature.slice();
  const state = {
    running: false, model, data, mapping,
    get time() { return data.time; },
    positions() { return mapping.map(j => data.qpos[j.qpos]); },
    setPositions(values) {
      mapping.forEach((j, i) => { data.qpos[j.qpos] = values[i] ?? 0; });
      data.qvel.fill(0); data.qfrc_applied.fill(0);
      mj.mj_forward(model, data);
    },
    gravity(enabled) { model.opt.gravity.set([0, 0, enabled ? -9.81 : 0]); },
    stabilize(enabled) {
      this.running = false; this.stabilized = enabled;
      model.dof_damping.set(originalDamping); model.dof_armature.set(originalArmature);
      if (enabled) for (const item of interaction?.joints || []) {
        const joint = mapping.find(j=>j.name===item.name);
        if (joint) { model.dof_damping[joint.dof]=item.damping; model.dof_armature[joint.dof]=item.armature; }
      }
      data.qvel.fill(0); data.qfrc_applied.fill(0); impulse=null;
      mj.mj_forward(model,data);
    },
    push(index, direction) {
      const joint = mapping[index];
      if (!joint || joint.mimic) return;
      const effort = interaction?.joints?.find(j=>j.name===joint.name)?.effort || (joint.effort > 0 ? joint.effort : 1);
      impulse = {dof: joint.dof, force: direction * effort * .5, end: data.time + .15};
      this.running = true;
    },
    step(delta) {
      if (!this.running || disposed) return;
      accumulator = Math.min(accumulator + delta, .06);
      let steps = 0;
      while (accumulator >= .002 && steps++ < 30) {
        data.qfrc_applied.fill(0);
        if (impulse && data.time < impulse.end) data.qfrc_applied[impulse.dof] = impulse.force;
        else impulse = null;
        const previous = data.qpos.slice();
        const excessive = () => mapping.some(j => {
          const speed = interaction?.joints?.find(item=>item.name===j.name)?.speed || (j.velocity > 0 ? j.velocity : j.type==='prismatic' ? .1 : 2);
          return !Number.isFinite(data.qpos[j.qpos]) || !Number.isFinite(data.qvel[j.dof]) || Math.abs(data.qvel[j.dof]) > 10 * speed;
        });
        const alreadyExcessive = excessive();
        if (!alreadyExcessive) mj.mj_step(model, data);
        if (alreadyExcessive || excessive()) {
          this.running = false; accumulator = 0; impulse = null;
          data.qpos.set(previous); data.qvel.fill(0); data.qfrc_applied.fill(0);
          mj.mj_forward(model,data);
          throw Error('Paused: excessive joint speed. Reset or adjust the joint pose before retrying.');
        }
        accumulator -= .002;
      }
      if (!mapping.every(j => Number.isFinite(data.qpos[j.qpos]))) {
        this.running = false;
        throw Error('Simulation stopped because the source model became unstable. Reset to try again.');
      }
    },
    reset() {
      this.running = false; accumulator = 0; impulse = null;
      mj.mj_resetData(model, data); mj.mj_forward(model, data);
    },
    dispose() {
      if (disposed) return;
      this.running = false; disposed = true; data.delete(); model.delete();
    },
  };
  mj.mj_forward(model, data);
  state.stabilize(true);
  return state;
}
