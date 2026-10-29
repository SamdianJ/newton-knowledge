"""One frozen native contact variant per independent process; read-only native diagnostics."""
from __future__ import annotations
import argparse, hashlib, json, platform, shutil, sys, traceback
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'manifests/source-lock.json').exists())
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def plain(x):
    if hasattr(x, 'tolist'): return plain(x.tolist())
    if isinstance(x, dict): return {k: plain(v) for k,v in x.items()}
    if isinstance(x, (list,tuple)): return [plain(v) for v in x]
    return x
def save(p,x): Path(p).write_text(json.dumps(plain(x),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
class Tee:
    def __init__(self,c,l): self.c,self.l=c,l
    def write(self,v): self.c.write(v); self.l.write(v); self.flush(); return len(v)
    def flush(self): self.c.flush(); self.l.flush()
def xml_scene(v):
    return f'''<mujoco model="newton_native_contact"><compiler angle="radian"/>
<option gravity="0 0 0" timestep="0.0005"><flag refsafe="enable"/></option>
<worldbody><geom name="floor" type="plane" size="2 2 0.1" priority="0" condim="1" friction="0 0 0" solimp="0.99 0.99 0.001 0.5 2" solref="0.08 1" margin="0" gap="0"/>
<body name="sphere" pos="0 0 0.15"><freejoint name="free"/><inertial pos="0 0 0" mass="1" diaginertia="0.001 0.001 0.001"/>
<geom name="ball" type="sphere" size="0.05" priority="1" condim="1" friction="0 0 0" solimp="0.99 0.99 0.001 0.5 2" solref="{v['solref'][0]} {v['solref'][1]}" margin="{v['margin']}" gap="{v['gap']}"/>
</body></worldbody></mujoco>'''
def main():
    a=argparse.ArgumentParser(); a.add_argument('--case',required=True); a.add_argument('--variant',choices=['A','B'],required=True); a.add_argument('--repeat',type=int,choices=[1,2],required=True); a.add_argument('--protocol',type=Path,required=True); a.add_argument('--expected-protocol-sha',required=True); args=a.parse_args()
    p=json.loads(args.protocol.read_text(encoding='utf8'))
    if sha(args.protocol)!=args.expected_protocol_sha or p['status']!='frozen_before_runs': raise ValueError('Frozen protocol SHA required')
    case=next(c for c in p['cases'] if c['id']==args.case); v=case['variants'][args.variant]
    rid=f"{args.case}_{args.variant}_r{args.repeat}_"+datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ'); out=HERE/'runs'/rid; out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,out/'runner.py'); shutil.copyfile(args.protocol,out/'protocol.json'); (out/'scene.xml').write_text(xml_scene(v),encoding='utf8')
    result={'run_id':rid,'case':args.case,'variant':args.variant,'repeat':args.repeat,'status':'started','run_directory':out.relative_to(ROOT).as_posix(),'program_sha256':sha(__file__),'protocol_sha256':sha(args.protocol),'scene_sha256':sha(out/'scene.xml'),'started_at':datetime.now(UTC).isoformat()}; save(out/'result.json',result)
    log=(out/'run.log').open('w',encoding='utf8'); oldout,olderr=sys.stdout,sys.stderr; sys.stdout,sys.stderr=Tee(oldout,log),Tee(olderr,log)
    rows=[]; steps=[]; code=0
    try:
        import numpy as np
        import warp as wp
        import newton, mujoco
        from newton.solvers import SolverMuJoCo
        lock=json.loads((ROOT/'manifests/source-lock.json').read_text(encoding='utf8')); installed=Path(newton.__file__).resolve().parent.parent
        locked={k:h for k,h in lock['files'].items() if k.startswith('newton/') and k.endswith('.py')}
        chk={'checked_python_files':len(locked),'missing':[k for k in locked if not (installed/k).is_file()],'changed':[k for k,h in locked.items() if (installed/k).is_file() and sha(installed/k)!=h]}; save(out/'installed-source-validation.json',chk)
        assert len(locked)==809 and not chk['missing'] and not chk['changed'],chk
        for ref in p['source_refs']: assert sha(ROOT/'sources/newton-v1.7.0'/ref['path'])==ref['sha256']
        for ref in p['official_sources']: assert sha(HERE/'source-material'/ref['file'])==ref['sha256']
        assert sha(HERE/'DESIGN.md')==p['design_sha256']
        assert version('mujoco')==p['mujoco_version'] and version('newton')==p['newton_version']
        save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'packages':{n:version(n) for n in ['numpy','warp-lang','newton','mujoco','mujoco-warp']},'device':'cpu','source_commit':p['source_commit'],'source_lock_sha256':sha(ROOT/'manifests/source-lock.json'),'installed_source_validation':chk,'source_refs':p['source_refs'],'official_sources':p['official_sources'],'native_diagnostics':'read-only mj_model/mj_data/mj_contactForce'})
        wp.init(); b=newton.ModelBuilder(); b.add_mjcf((out/'scene.xml').read_text(),ignore_inertial_definitions=False,legacy_margin_gap=False)
        model=b.finalize(device='cpu'); model.set_gravity((0.,0.,0.)); initial=model.joint_qd.numpy(); assert initial.shape==(6,); initial[2]=-1.; model.joint_qd.assign(initial)
        solver=SolverMuJoCo(model,**p['solver']); state=model.state(); nxt=model.state(); control=model.control(); newton.eval_fk(model,model.joint_q,model.joint_qd,state)
        m,d=solver.mj_model,solver.mj_data
        resolved={'requested':p['solver'],'variant':v,'use_mujoco_cpu':solver.use_mujoco_cpu,'zero_margins_for_native_ccd':solver._zero_margins_for_native_ccd,'native_option_sampling':'after_construction_before_first_step; actual timestep recorded per step','native_option':{k:plain(getattr(m.opt,k)) for k in ['timestep','iterations','tolerance','solver','integrator','enableflags','disableflags','gravity']},'refsafe_enabled':not bool(m.opt.disableflags & int(mujoco.mjtDisableBit.mjDSBL_REFSAFE)),'native_geom':{k:plain(getattr(m,k)) for k in ['geom_type','geom_bodyid','geom_priority','geom_solref','geom_solimp','geom_margin','geom_gap','geom_condim','geom_friction']},'native_body_mass':m.body_mass,'native_body_inertia':m.body_inertia}
        resolved['newton']={k:getattr(model,k).numpy() for k in ['shape_margin','shape_gap','shape_material_ke','shape_material_kd','body_mass','body_inertia']}
        resolved['custom']={k:getattr(model.mujoco,k).numpy() for k in ['solref','solref_mode','geom_priority','geom_solimp']}; save(out/'resolved-config.json',resolved)
        assert solver.use_mujoco_cpu and not solver._zero_margins_for_native_ccd and resolved['refsafe_enabled']
        def snap(s): return {k:getattr(s,k).numpy().copy() for k in ['body_q','body_qd','joint_q','joint_qd']}
        rows.append(snap(state)); dt=p['run']['dt_s']
        for n in range(p['run']['steps']):
            state.clear_forces(); solver.step(state,nxt,control=control,contacts=None,dt=dt)
            assert d.ncon<=1, 'Expected one sphere-plane contact'
            r={'native_timestep':float(m.opt.timestep),'native_time_after_step':float(d.time),'ncon':d.ncon,'nefc':d.nefc,'contact_valid':bool(d.ncon),'contact_dist':0.,'contact_includemargin':0.,'contact_efc_address':-1,'contact_solref':np.zeros(2),'contact_solimp':np.zeros(5),'contact_normal_force':0.,'qfrc_constraint':d.qfrc_constraint.copy(),'native_qpos':d.qpos.copy(),'native_qvel':d.qvel.copy(),'solver_niter':d.solver_niter.copy(),'solver_fwdinv':d.solver_fwdinv.copy()}
            if d.ncon:
                c=d.contact[0]; force=np.zeros(6); mujoco.mj_contactForce(m,d,0,force)
                r.update(contact_dist=float(c.dist),contact_includemargin=float(c.includemargin),contact_efc_address=int(c.efc_address),contact_solref=c.solref.copy(),contact_solimp=c.solimp.copy(),contact_normal_force=float(force[0]))
            steps.append(r); rows.append(snap(nxt)); state,nxt=nxt,state
        arrays={k:np.stack([r[k] for r in rows]) for k in rows[0]}; arrays['t']=np.arange(len(rows))*dt
        arrays.update({'step_'+k:np.asarray([s[k] for s in steps]) for k in steps[0]}); arrays['step_time']=arrays['t'][:-1]; np.savez_compressed(out/'trajectory.npz',**arrays)
        result.update(status='completed',samples=len(rows),raw_sha256=sha(out/'trajectory.npz'),config_sha256=sha(out/'resolved-config.json'),note='Completion separate from frozen physical acceptance')
    except Exception as exc:
        code=1; traceback.print_exc(); result.update(status='failed',error=repr(exc))
        if rows: np.savez_compressed(out/'trajectory-partial.npz',**{k:np.stack([r[k] for r in rows]) for k in rows[0]})
        if steps: np.savez_compressed(out/'contact-partial.npz',**{k:np.asarray([r[k] for r in steps]) for k in steps[0]})
    finally:
        sys.stdout.flush(); sys.stderr.flush(); sys.stdout,sys.stderr=oldout,olderr; log.close(); result['finished_at']=datetime.now(UTC).isoformat(); result['files_sha256']={f.name:sha(f) for f in out.iterdir() if f.is_file() and f.name!='result.json'}; save(out/'result.json',result); print(json.dumps({'status':result['status'],'run':result['run_directory']}))
    raise SystemExit(code)
if __name__=='__main__': main()
