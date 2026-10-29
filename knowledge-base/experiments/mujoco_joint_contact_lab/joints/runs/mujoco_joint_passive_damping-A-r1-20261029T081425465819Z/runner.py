"""One frozen Newton/native-MuJoCo joint experiment; every attempt retained."""
from pathlib import Path
import argparse, hashlib, json, math, platform, shutil, sys, time, traceback
from datetime import datetime, timezone
from importlib.metadata import version
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'manifests/source-lock.json').exists())
sys.dont_write_bytecode=True
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def plain(v):
    if isinstance(v,dict):return {k:plain(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [plain(x) for x in v]
    if hasattr(v,'tolist'):return plain(v.tolist())
    if isinstance(v,float) and not math.isfinite(v):return str(v)
    return v
def save(p,v):p.write_text(json.dumps(plain(v),indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
class Tee:
    def __init__(self,a,b):self.a,self.b=a,b
    def write(self,s):self.a.write(s);self.b.write(s);self.flush();return len(s)
    def flush(self):self.a.flush();self.b.flush()
def state_sample(state,solver):
    r={k:getattr(state,k).numpy().copy() for k in ('body_q','body_qd','joint_q','joint_qd')}
    r.update(native_qpos=solver.mj_data.qpos.copy(),native_qvel=solver.mj_data.qvel.copy())
    return r
def actual(model,solver):
    m=solver.mj_model
    keys=('body_mass','body_inertia','body_ipos','jnt_type','jnt_range','jnt_limited','jnt_margin','jnt_solref','jnt_solimp','jnt_actfrcrange','jnt_actfrclimited','dof_armature','dof_damping','dof_frictionloss','dof_invweight0','actuator_gainprm','actuator_biasprm','actuator_gear','actuator_trnid')
    return {'mj_model':{k:getattr(m,k).copy() for k in keys},'counts':{k:int(getattr(m,k)) for k in ('nq','nv','nu','njnt','nbody','ngeom')},'opt':{k:plain(getattr(m.opt,k)) for k in ('timestep','integrator','solver','iterations','tolerance','disableflags','enableflags','gravity')},'native_qM_initial':solver.mj_data.qM.copy(),'newton':{k:getattr(model,k).numpy().copy() for k in ('body_mass','body_inertia','body_com','joint_damping','joint_armature','joint_target_ke','joint_target_kd','joint_target_mode','joint_limit_lower','joint_limit_upper','joint_limit_ke','joint_limit_kd')},'use_mujoco_cpu':solver.use_mujoco_cpu,'update_data_interval':solver.update_data_interval}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',type=Path,required=True);ap.add_argument('--expected-protocol-sha',required=True);ap.add_argument('--case',required=True);ap.add_argument('--variant',choices=('A','B'),required=True);ap.add_argument('--repeat',type=int,choices=(1,2),required=True);a=ap.parse_args()
    p=json.loads(a.protocol.read_text(encoding='utf8'))
    if p.get('status')!='frozen_before_runs' or sha(a.protocol)!=a.expected_protocol_sha:raise ValueError('Require frozen protocol hash')
    case=next(c for c in p['cases'] if c['id']==a.case);cfg={**case['base'],**case['variants'][a.variant]}
    run_id=f"{a.case}-{a.variant}-r{a.repeat}-"+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=HERE/'runs'/run_id;out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(a.protocol,out/'protocol.json');shutil.copy2(__file__,out/'runner.py')
    result={'run_id':run_id,'case':a.case,'variant':a.variant,'repeat':a.repeat,'status':'started','protocol_sha256':sha(a.protocol),'runner_sha256':sha(__file__),'started_at_utc':datetime.now(timezone.utc).isoformat()};save(out/'result.json',result)
    log=(out/'run.log').open('w',encoding='utf8');oldout,olderr=sys.stdout,sys.stderr;sys.stdout,sys.stderr=Tee(oldout,log),Tee(olderr,log)
    rows=[];forces=[];elapsed=[];rc=0
    try:
        import numpy as np
        import warp as wp
        import newton
        import mujoco
        from newton.solvers import SolverMuJoCo
        installed=Path(newton.__file__).resolve().parent.parent
        lock=json.loads((ROOT/'manifests/source-lock.json').read_text(encoding='utf8'));expected={k:v for k,v in lock['files'].items() if k.startswith('newton/') and k.endswith('.py')}
        src={'checked_python_files':len(expected),'missing':[k for k in expected if not(installed/k).exists()],'changed':[k for k,v in expected.items() if(installed/k).exists() and sha(installed/k)!=v],'source_lock_sha256':sha(ROOT/'manifests/source-lock.json')}
        save(out/'installed-source-validation.json',src)
        if src['checked_python_files']!=809 or src['missing'] or src['changed']:raise ValueError('Installed Newton differs from locked 809 Python sources')
        if version('mujoco')!=p['native_mujoco_version']:raise ValueError('Native MuJoCo version differs from frozen protocol')
        save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'packages':{k:version(k) for k in ('numpy','warp-lang','newton','mujoco')},'device':'cpu','source_commit':p['source_commit'],'source_validation':src,'source_refs_sha256':{r['path']:sha(ROOT/'sources/newton-v1.7.0'/r['path']) for r in p['source_refs']},'instrumentation':'Read-only native mj_model/mj_data observations; Newton ModelBuilder/SolverMuJoCo public scene/step API.'})
        wp.init();b=newton.ModelBuilder();SolverMuJoCo.register_custom_attributes(b);b.begin_world()
        body=b.add_link(mass=1.,inertia=[1.,0.,0.,0.,1.,0.,0.,0.,1.],com=wp.vec3(0,0,0),lock_inertia=True)
        joint=b.add_joint_revolute(-1,body,axis=newton.Axis.Y,damping=cfg['damping'],armature=cfg['armature'],target_ke=cfg['kp'],target_kd=cfg['kd'],target_pos=cfg['qref'],actuator_mode=getattr(newton.JointTargetMode,cfg['mode']),effort_limit=100.,friction=0.,limit_lower=cfg['limit_lower'],limit_upper=cfg['limit_upper'],limit_ke=cfg['limit_ke'],limit_kd=cfg['limit_kd'])
        b.add_articulation([joint]);b.end_world();b.joint_q[0]=0.;b.joint_qd[0]=cfg['initial_v']
        model=b.finalize(device='cpu');model.set_gravity((0,0,0));state=model.state();output=model.state();control=model.control();newton.eval_fk(model,model.joint_q,model.joint_qd,state)
        solver=SolverMuJoCo(model,**p['solver']);resolved=actual(model,solver);resolved.update(treatment=cfg,requested=p['solver']);save(out/'resolved-config.json',resolved)
        rows.append(state_sample(state,solver));dt=p['run']['dt_s']
        for n in range(p['run']['steps']):
            state.clear_forces();control.joint_f.fill_(cfg['external_tau']);control.joint_target_q.fill_(cfg['qref']);control.joint_target_qd.zero_()
            start=time.perf_counter();solver.step(state,output,control=control,contacts=None,dt=dt)
            d=solver.mj_data
            force={k:getattr(d,k).copy() for k in ('qfrc_passive','qfrc_actuator','qfrc_applied','qfrc_constraint','qacc','qM','solver_niter')}
            force['nefc']=np.asarray(d.nefc);force['warning_number']=d.warning.number.copy();forces.append(force)
            rows.append(state_sample(output,solver));elapsed.append(time.perf_counter()-start);state,output=output,state
        resolved['opt_final']=actual(model,solver)['opt'];save(out/'resolved-config.json',resolved)
        result['status']='completed'
    except Exception as exc:
        result.update(status='failed',error=repr(exc));traceback.print_exc();rc=1
    finally:
        if rows:
            try:
                arrays={k:np.stack([r[k] for r in rows]) for k in rows[0]};arrays['t']=np.arange(len(rows))*p['run']['dt_s'];arrays['force_t']=np.arange(len(forces))*p['run']['dt_s']
                if forces:arrays.update({k:np.stack([r[k] for r in forces]) for k in forces[0]})
                arrays['step_wall_s']=np.asarray(elapsed);np.savez_compressed(out/'trajectory.npz',**arrays);result['samples']=len(rows)
            except Exception as exc:result.update(status='failed',serialization_error=repr(exc));traceback.print_exc();rc=1
        result['finished_at_utc']=datetime.now(timezone.utc).isoformat();sys.stdout.flush();sys.stderr.flush();sys.stdout,sys.stderr=oldout,olderr;log.close()
        result['files_sha256']={f.name:sha(f) for f in sorted(out.iterdir()) if f.is_file() and f.name!='result.json'};save(out/'result.json',result);print(json.dumps({'run_id':run_id,'status':result['status']}))
    raise SystemExit(rc)
if __name__=='__main__':main()
