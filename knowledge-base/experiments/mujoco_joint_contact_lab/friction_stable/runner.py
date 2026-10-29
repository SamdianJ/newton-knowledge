"""One immutable native-CPU friction experiment from a frozen protocol."""
from __future__ import annotations
import argparse, hashlib, inspect, json, math, platform, shutil, sys, traceback
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'manifests/source-lock.json').exists())
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def plain(x):
    if hasattr(x, 'tolist'): return plain(x.tolist())
    if isinstance(x, dict): return {str(k): plain(v) for k,v in x.items()}
    if isinstance(x, (tuple,list)): return [plain(v) for v in x]
    if isinstance(x, float) and not math.isfinite(x): return str(x)
    return x
def save(p,x): Path(p).write_text(json.dumps(plain(x),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
class Tee:
    def __init__(self,console,log): self.console,self.log=console,log
    def write(self,s): self.console.write(s); self.log.write(s); self.flush(); return len(s)
    def flush(self): self.console.flush(); self.log.flush()

def build(np,wp,newton,SolverMuJoCo,p,c,v,out):
    b=newton.ModelBuilder()
    SolverMuJoCo.register_custom_attributes(b)
    common=p['common_scene']; treatment=c['variants'][v]
    def cfg(mu,torsion,rolling):
        return newton.ModelBuilder.ShapeConfig(density=0.,mu=mu,mu_torsional=torsion,mu_rolling=rolling,margin=0.)
    def attrs(dim):
        return {'mujoco:condim':dim,'mujoco:geom_priority':0,
                'mujoco:solref':common['raw_solref'],'mujoco:solref_mode':1,
                'mujoco:geom_solimp':common['raw_solimp'],'mujoco:geom_solmix':1.}
    b.begin_world()
    b.add_shape_plane(width=0.,length=0.,cfg=cfg(0.,0.,0.),label='ground',custom_attributes=attrs(3))
    height=c.get('radius_m',c.get('half_extents_m',[0,0,0])[2])-common['initial_penetration_m']
    inertia=np.diag(c['inertia_diagonal_kg_m2']).reshape(-1).tolist()
    body=b.add_link(xform=wp.transform(wp.vec3(0.,0.,height),wp.quat_identity()),mass=1.,inertia=inertia,com=wp.vec3(0.),lock_inertia=True,label='specimen')
    j=b.add_joint_free(body,label='free'); b.add_articulation([j])
    options=dict(cfg=cfg(treatment['body_mu'],c['body_mu_torsional_m'],c['body_mu_rolling_m']),label='specimen_geom',custom_attributes=attrs(treatment['body_condim']))
    if c['shape']=='box': b.add_shape_box(body,hx=c['half_extents_m'][0],hy=c['half_extents_m'][1],hz=c['half_extents_m'][2],**options)
    else: b.add_shape_sphere(body,radius=c['radius_m'],**options)
    b.joint_qd[:]=c['initial_velocity_world']
    b.end_world()
    model=b.finalize(device='cpu'); model.set_gravity(common['gravity_m_s2'])
    state=model.state(); newton.eval_fk(model,model.joint_q,model.joint_qd,state)
    options={k:v for k,v in p['solver'].items() if k!='interpretation'}
    solver=SolverMuJoCo(model,save_to_mjcf=str(out/'model.xml'),**options)
    return model,solver,state,model.control()

def resolved(np,mujoco,model,s,p,c,v):
    m=s.mj_model
    dynamic=np.flatnonzero(m.geom_bodyid!=0); ground=np.flatnonzero(m.geom_bodyid==0)
    assert len(dynamic)==len(ground)==1, 'Exactly one dynamic geom and one ground required'
    dg,gg=int(dynamic[0]),int(ground[0])
    enum={'solver':int(mujoco.mjtSolver.mjSOL_NEWTON),'integrator':int(mujoco.mjtIntegrator.mjINT_EULER),'cone':int(mujoco.mjtCone.mjCONE_ELLIPTIC),'jacobian':int(mujoco.mjtJacobian.mjJAC_DENSE)}
    for k,value in enum.items(): assert p['solver'][k]==value and int(getattr(m.opt,k))==value
    assert s.use_mujoco_cpu and s._use_mujoco_contacts and s.update_data_interval==1
    fields=['geom_bodyid','geom_type','geom_size','geom_pos','geom_quat','geom_friction','geom_condim','geom_priority','geom_solref','geom_solimp','geom_solmix','geom_margin','geom_gap','geom_contype','geom_conaffinity','body_mass','body_inertia','body_ipos','body_iquat','dof_damping','dof_frictionloss','dof_armature','jnt_type']
    data={k:getattr(m,k).copy() for k in fields}
    data['snapshot_phase']='before_first_step; options.timestep is constructor default; actual each-step value is trajectory.native_timestep'
    data.update(treatment=c['variants'][v],dynamic_geom=dg,ground_geom=gg,backend={'use_mujoco_cpu':s.use_mujoco_cpu,'use_mujoco_contacts':s._use_mujoco_contacts,'update_data_interval':s.update_data_interval},options={k:plain(getattr(m.opt,k)) for k in ('solver','integrator','cone','jacobian','iterations','tolerance','ls_iterations','impratio','gravity','timestep')},enum=enum,newton_body_mass=model.body_mass.numpy().copy(),newton_body_inertia=model.body_inertia.numpy().copy(),newton_body_com=model.body_com.numpy().copy(),body_names=['specimen'])
    assert m.npair==0 and m.nu==0
    np.testing.assert_allclose(m.geom_friction[dg],[c['variants'][v]['body_mu'],c['body_mu_torsional_m'],c['body_mu_rolling_m']],rtol=1e-6,atol=1e-10)
    np.testing.assert_array_equal(m.geom_friction[gg],[0,0,0])
    assert m.geom_condim[dg]==c['variants'][v]['body_condim'] and m.geom_condim[gg]==3
    np.testing.assert_allclose(m.body_mass[m.geom_bodyid[dg]],1.)
    # MuJoCo may reorder diagonal principal axes; trace and eigenvalues are invariant.
    np.testing.assert_allclose(np.sort(m.body_inertia[m.geom_bodyid[dg]]),np.sort(c['inertia_diagonal_kg_m2']),rtol=1e-6)
    return data

def state_row(state):
    return {k:getattr(state,k).numpy().copy() for k in ('body_q','body_qd','joint_q','joint_qd')}

def simulate(np,mujoco,model,s,state,control,p,c,config,out):
    dt=p['run']['dt_s']; rows=[state_row(state)]; contacts=[]
    other=model.state(); m=s.mj_model; d=s.mj_data; dg=config['dynamic_geom']; gg=config['ground_geom']
    try:
        for step in range(c['steps']):
            pre_com=rows[-1]['body_q'][0,:3].astype(float).copy()
            state.clear_forces(); s.step(state,other,control,None,dt)
            n=int(d.ncon)
            if n>16: raise RuntimeError('Contact export capacity exceeded; no truncation permitted')
            row={'ncon':n,'contact_dim':np.zeros(16,dtype=int),'contact_geom':np.full((16,2),-1,dtype=int),'contact_dist':np.zeros(16),'contact_pos':np.zeros((16,3)),'contact_frame':np.zeros((16,3,3)),'contact_friction':np.zeros((16,5)),'contact_solref':np.zeros((16,2)),'contact_solimp':np.zeros((16,5)),'contact_efc_address':np.full(16,-1,dtype=int),'contact_wrench':np.zeros((16,6)),'world_contact_force':np.zeros(3),'world_contact_torque':np.zeros(3),'pre_com':pre_com,'native_qpos':d.qpos.copy(),'native_qvel':d.qvel.copy(),'native_qacc':d.qacc.copy(),'native_qfrc_constraint':d.qfrc_constraint.copy(),'solver_niter':d.solver_niter.copy(),'warning_number':d.warning.number.copy()}
            for k in range(n):
                con=d.contact[k]; wrench=np.zeros(6); mujoco.mj_contactForce(m,d,k,wrench)
                pair=[int(con.geom1),int(con.geom2)]
                if set(pair)!={dg,gg}: raise RuntimeError('Unexpected geom contact pair')
                sign=1. if pair[1]==dg else -1.
                frame=con.frame.copy().reshape(3,3); force=sign*frame.T@wrench[:3]
                torque=sign*frame.T@wrench[3:]+np.cross(con.pos-pre_com,force)
                for key,value in [('dim',con.dim),('geom',pair),('dist',con.dist),('pos',con.pos),('frame',frame),('friction',con.friction),('solref',con.solref),('solimp',con.solimp),('efc_address',con.efc_address),('wrench',wrench)]: row['contact_'+key][k]=value
                row['world_contact_force']+=force; row['world_contact_torque']+=torque
            row['native_nefc']=int(d.nefc)
            if d.nefc>64: raise RuntimeError('Constraint diagnostic export capacity exceeded')
            for field,shape in [('R',(64,)),('KBIP',(64,4)),('aref',(64,)),('force',(64,)),('vel',(64,)),('b',(64,)),('J',(64,m.nv)),('pos',(64,)),('margin',(64,))]:
                exported=np.zeros(shape); observed=np.asarray(getattr(d,'efc_'+field)).copy()
                observed=observed.reshape((-1,shape[1])) if len(shape)==2 else observed
                exported[:d.nefc]=observed[:d.nefc]; row['native_efc_'+field]=exported
            row['native_contact_regularized_mu']=np.zeros(16)
            for k in range(n): row['native_contact_regularized_mu'][k]=d.contact[k].mu
            row['native_timestep']=float(m.opt.timestep)
            if abs(row['native_timestep']-dt)>1e-12: raise RuntimeError('Native timestep differs from frozen step argument')
            contacts.append(row); state,other=other,state; rows.append(state_row(state))
    finally:
        arrays={k:np.asarray([r[k] for r in rows]) for k in rows[0]}; arrays['t']=np.arange(len(rows))*dt
        if contacts: arrays.update({k:np.asarray([r[k] for r in contacts]) for k in contacts[0]})
        np.savez_compressed(out/'trajectory.npz',**arrays)
    return arrays

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--protocol',type=Path,required=True); parser.add_argument('--expected-protocol-sha',required=True); parser.add_argument('--case',required=True); parser.add_argument('--variant',choices=['A','B'],required=True); parser.add_argument('--repeat',type=int,choices=[1,2],required=True)
    args=parser.parse_args(); p=json.loads(args.protocol.read_text(encoding='utf-8-sig'))
    assert sha(args.protocol)==args.expected_protocol_sha and p['status']=='frozen_before_runs'
    c=next(x for x in p['cases'] if x['id']==args.case)
    stamp=datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ'); out=HERE/'runs'/f'{args.case}_{args.variant}_r{args.repeat}_{stamp}'; out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,out/'runner.py'); shutil.copyfile(args.protocol,out/'protocol.json'); save(out/'scene.json',c)
    result={'case':c['id'],'variant':args.variant,'repeat':args.repeat,'run_id':out.name,'run_directory':out.relative_to(ROOT).as_posix(),'status':'started','started_at':datetime.now(UTC).isoformat(),'runner_sha256':sha(__file__),'protocol_sha256':sha(args.protocol)}; save(out/'result.json',result)
    log=(out/'run.log').open('w',encoding='utf-8'); oldout,olderr=sys.stdout,sys.stderr; sys.stdout,sys.stderr=Tee(oldout,log),Tee(olderr,log); exitcode=0
    try:
        import numpy as np
        import warp as wp
        import newton, mujoco
        from newton.solvers import SolverMuJoCo
        lock=json.loads((ROOT/'manifests/source-lock.json').read_text(encoding='utf-8')); installed=Path(newton.__file__).resolve().parent.parent
        locked={k:h for k,h in lock['files'].items() if k.startswith('newton/') and k.endswith('.py')}
        actual={k:sha(installed/k) if (installed/k).is_file() else None for k in locked}
        validation={'checked_python_files':len(locked),'installed_parent':str(installed),'expected':locked,'actual':actual,'mismatches':[k for k in locked if locked[k]!=actual[k]]}; save(out/'installed-source-validation.json',validation)
        assert len(locked)==809 and not validation['mismatches'] and lock['commit']==p['source_commit']
        assert version('mujoco')==p['native_mujoco_version']
        native=Path(mujoco.__file__).resolve().parent
        env={'python':sys.version,'platform':platform.platform(),'device':'cpu','packages':{n:version(n) for n in ('numpy','warp-lang','newton','mujoco','mujoco-warp')},'source_commit':lock['commit'],'source_lock_sha256':sha(ROOT/'manifests/source-lock.json'),'wrapper_path':inspect.getfile(SolverMuJoCo),'wrapper_sha256':sha(inspect.getfile(SolverMuJoCo)),'native_libraries':{f.relative_to(native).as_posix():sha(f) for f in native.rglob('*') if f.is_file() and f.suffix.lower() in ('.dll','.pyd')},'instrumentation':'Read-only native MjModel/MjData and mj_contactForce. No Newton CONTACT_F request.'}; save(out/'environment.json',env)
        wp.init(); model,s,state,control=build(np,wp,newton,SolverMuJoCo,p,c,args.variant,out)
        config=resolved(np,mujoco,model,s,p,c,args.variant); save(out/'resolved-config.json',config)
        arrays=simulate(np,mujoco,model,s,state,control,p,c,config,out)
        result.update(status='completed',samples=len(arrays['t']),raw_sha256=sha(out/'trajectory.npz'),note='Completion is not physical acceptance')
    except Exception as exc:
        exitcode=1; traceback.print_exc(); result.update(status='failed',error=repr(exc))
    finally:
        sys.stdout.flush(); sys.stderr.flush(); sys.stdout,sys.stderr=oldout,olderr; log.close()
        result['finished_at']=datetime.now(UTC).isoformat(); result['files_sha256']={f.name:sha(f) for f in sorted(out.iterdir()) if f.is_file() and f.name!='result.json'}; save(out/'result.json',result); print(json.dumps({'status':result['status'],'run':result['run_directory']}))
    raise SystemExit(exitcode)
if __name__=='__main__': main()
