"""Small contact execution probe; this is not a completed parameter A/B."""
import argparse
import dataclasses
import hashlib
import inspect
import json
import math
import platform
import sys
import traceback
from importlib.metadata import version
from pathlib import Path

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--solver',choices=['mujoco','kamino'],required=True);args=parser.parse_args()
    result={'solver':args.solver,'status':'probe_started','counts_as_ab':False,'python':platform.python_version(),
            'executable':sys.executable,'packages':{n:version(n) for n in ['newton','numpy','warp-lang','mujoco','mujoco-warp']}}
    try:
        import newton
        import warp as wp
        wp.init();result['warp_devices']=[str(d) for d in wp.get_devices()]
        cls=newton.solvers.SolverMuJoCo if args.solver=='mujoco' else newton.solvers.SolverKamino
        path=Path(inspect.getfile(cls));relative='newton/_src/solvers/'+args.solver+'/solver_'+args.solver+'.py'
        locked=json.loads((ROOT/'manifests/source-lock.json').read_text())['files'][relative]
        result['solver_source']={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'manifest_sha256':locked}
        if result['solver_source']['sha256']!=locked:raise RuntimeError('Installed solver source does not match pinned snapshot')
        with wp.ScopedDevice('cpu'):
            builder=newton.ModelBuilder(up_axis=newton.Axis.Z)
            builder.add_ground_plane(cfg=newton.ModelBuilder.ShapeConfig(mu=.5,ke=20000,kd=300))
            builder.begin_world();body=builder.add_body(xform=wp.transform(wp.vec3(0,0,.095),wp.quat_identity()),label='probe_sphere')
            cfg=newton.ModelBuilder.ShapeConfig(density=1/(4/3*math.pi*.1**3),mu=.5,ke=20000,kd=300)
            builder.add_shape_sphere(body=body,radius=.1,cfg=cfg);builder.end_world()
            model=builder.finalize(device='cpu');state0=model.state();state1=model.state();control=model.control()
            newton.eval_fk(model,model.joint_q,model.joint_qd,state0)
            if args.solver=='mujoco':solver=cls(model,use_mujoco_cpu=True,use_mujoco_contacts=True,iterations=5)
            else:
                config=cls.Config(dynamics_solver='padmm',use_collision_detector=True)
                for key in ('padmm','dvi','fk'):
                    section=getattr(config,key,None)
                    if hasattr(section,'use_graph_conditionals'):section.use_graph_conditionals=False
                config.padmm.max_iterations=4;config.collision_detector.max_contacts_per_world=16
                result['requested_config']=dataclasses.asdict(config)
                solver=cls(model,config=config)
            result['heights']=[float(state0.body_q.numpy()[0,2])]
            for _ in range(8):
                state0.clear_forces();solver.step(state0,state1,control,None,1/240);state0,state1=state1,state0
                result['heights'].append(float(state0.body_q.numpy()[0,2]))
            if args.solver=='kamino':
                status=solver.status.numpy();result['terminal_status']={n:status[n].tolist() for n in status.dtype.names}
            else:
                result['native_options']={'iterations':solver.mj_model.opt.iterations,'geom_solref':solver.mj_model.geom_solref.tolist(),'ncon':solver.mj_data.ncon}
            result['status']='probe_passed'
    except Exception as exc:
        result.update(status='probe_failed',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
    target=Path(__file__).parent/('environment-probe-'+args.solver+'.json')
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print('PROBE_RESULT '+json.dumps({k:v for k,v in result.items() if k not in ('traceback','requested_config')},ensure_ascii=False,default=str),flush=True)
    if result['status']!='probe_passed':raise SystemExit(1)

if __name__=='__main__':main()
