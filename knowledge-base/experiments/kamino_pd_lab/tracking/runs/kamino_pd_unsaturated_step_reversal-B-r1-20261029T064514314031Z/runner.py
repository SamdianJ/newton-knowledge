"""One frozen unsaturated PD experiment; failed attempts are retained."""
from __future__ import annotations
import argparse
import dataclasses
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from importlib.metadata import version

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "manifests/source-lock.json").exists())
sys.dont_write_bytecode = True
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def plain(v):
    if dataclasses.is_dataclass(v): return {f.name:plain(getattr(v,f.name)) for f in dataclasses.fields(v)}
    if isinstance(v,dict): return {str(k):plain(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)): return [plain(x) for x in v]
    if hasattr(v,"tolist"): return plain(v.tolist())
    if isinstance(v,float) and not math.isfinite(v): return str(v)
    if v is None or isinstance(v,(str,int,float,bool)): return v
    return {"type":type(v).__module__+"."+type(v).__qualname__}
def save(p,v): p.write_text(json.dumps(plain(v),ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
class Tee:
    def __init__(self,a,b): self.a,self.b=a,b
    def write(self,s): self.a.write(s); self.b.write(s); self.flush(); return len(s)
    def flush(self): self.a.flush(); self.b.flush()

def snapshot(state, solver):
    out = {k:getattr(state,k).numpy().copy() for k in ("body_q","body_qd","joint_q","joint_qd","body_qdd")}
    internal = solver._solver_kamino.data
    value = getattr(state,"joint_lambdas_tau",None)
    out["joint_lambdas_tau"] = (value if value is not None else internal.joints.lambda_tau_j).numpy().copy()
    out["applied_body_wrench"] = internal.bodies.w_a_i.numpy().copy()
    status = solver.status.numpy()
    for key in ("converged","iterations","r_p","r_d","r_c"):
        out["status_"+key] = status[key].copy()
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--protocol",type=Path,required=True)
    ap.add_argument("--expected-protocol-sha",required=True)
    ap.add_argument("--case",required=True)
    ap.add_argument("--variant",choices=("A","B"),required=True)
    ap.add_argument("--repeat",type=int,choices=(1,2),required=True)
    args=ap.parse_args()
    protocol=json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol.get("status") != "frozen_before_runs" or sha(args.protocol)!=args.expected_protocol_sha:
        raise ValueError("Require root-frozen protocol with explicit SHA256")
    case=next(c for c in protocol["cases"] if c["id"]==args.case)
    variant=case["variants"][args.variant]
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id=f"{args.case}-{args.variant}-r{args.repeat}-{stamp}"
    out=HERE/"runs"/run_id
    out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(args.protocol,out/"protocol.json")
    shutil.copy2(Path(__file__),out/"runner.py")
    result={"run_id":run_id,"case":args.case,"variant":args.variant,"repeat":args.repeat,"status":"started","protocol_sha256":sha(args.protocol),"runner_sha256":sha(Path(__file__)),"started_at_utc":datetime.now(timezone.utc).isoformat()}
    save(out/"result.json",result)
    log=(out/"run.log").open("w",encoding="utf-8")
    old_stdout,old_stderr=sys.stdout,sys.stderr
    sys.stdout,sys.stderr=Tee(old_stdout,log),Tee(old_stderr,log)
    rows,commands,elapsed=[],[],[]
    exit_code=0
    try:
        import numpy as np
        import warp as wp
        import newton
        from newton.solvers import SolverKamino
        installed=Path(newton.__file__).resolve().parent.parent
        locked=json.loads((ROOT/"manifests/source-lock.json").read_text(encoding="utf-8"))
        expected={p:h for p,h in locked["files"].items() if p.startswith("newton/") and p.endswith(".py")}
        missing=[p for p in expected if not (installed/p).exists()]
        changed=[p for p,h in expected.items() if (installed/p).exists() and sha(installed/p)!=h]
        source={"checked_python_files":len(expected),"missing":missing,"changed":changed,"installed_parent":str(installed),"source_lock_sha256":sha(ROOT/"manifests/source-lock.json")}
        save(out/"installed-source-validation.json",source)
        if len(expected)!=809 or missing or changed: raise ValueError("Installed source does not match all 809 locked Python files")
        env={"python":sys.version,"platform":platform.platform(),"packages":{n:version(n) for n in ("numpy","warp-lang","newton")},"device":"cpu","source_commit":protocol["source_commit"],"installed_source_validation":source,"source_refs_sha256":{s["path"]:sha(ROOT/"sources/newton-v1.7.0"/s["path"]) for s in protocol["source_refs"]},"private_instrumentation":["_model_kamino.joints.dof_act_paths","_solver_kamino.data.bodies.w_a_i","_solver_kamino.data.joints.lambda_tau_j initial fallback"]}
        save(out/"environment.json",env)
        wp.init()
        scene=protocol["scene"]
        builder=newton.ModelBuilder()
        SolverKamino.register_custom_attributes(builder)
        builder.begin_world()
        body=builder.add_link(mass=scene["mass_kg"],inertia=np.asarray(scene["inertia_com_kg_m2"]).reshape(-1).tolist(),com=wp.vec3(*scene["com_in_body_m"]),lock_inertia=True)
        joint=builder.add_joint_revolute(-1,body,axis=newton.Axis.Y,effort_limit=scene["effort_limit_Nm"],target_ke=scene["kp_Nm_per_rad"],target_kd=scene["kd_Nm_s_per_rad"],armature=0.,actuator_mode=getattr(newton.JointTargetMode,variant["target_mode"]))
        builder.add_articulation([joint])
        builder.end_world()
        model=builder.finalize(device="cpu")
        model.set_gravity(tuple(scene["gravity"]))
        model.request_state_attributes("body_qdd")
        config=SolverKamino.Config(dynamics_solver="padmm")
        config_mapping={"solver.constraints.preconditioning":"SolverKamino.Config.dynamics.preconditioning"}
        for key,value in protocol["solver"].items():
            # Frozen protocol's constraints label means constrained-dynamics
            # preconditioning; API owns this field on dynamics, not stabilization.
            api_key="dynamics" if key=="constraints" else key
            if key in ("padmm","constraints"):
                for name,item in value.items():
                    if not hasattr(getattr(config,api_key),name): raise ValueError("Unknown config field "+api_key+"."+name)
                    setattr(getattr(config,api_key),name,item)
            else: setattr(config,key,value)
        solver=SolverKamino(model,config=config)
        state=model.state()
        newton.eval_fk(model,model.joint_q,model.joint_qd,state)
        output=model.state()
        control=model.control()
        config_out={"solver":plain(config),"protocol_to_api_mapping":config_mapping,"target_mode":variant["target_mode"],"body_mass":model.body_mass.numpy(),"body_inertia":model.body_inertia.numpy(),"body_com":model.body_com.numpy(),"joint_target_mode":model.joint_target_mode.numpy(),"dof_act_paths":solver._model_kamino.joints.dof_act_paths.numpy(),"joint_target_ke":model.joint_target_ke.numpy(),"joint_target_kd":model.joint_target_kd.numpy(),"joint_effort_limit":model.joint_effort_limit.numpy()}
        save(out/"resolved-config.json",config_out)
        rows.append(snapshot(state,solver))
        dt=protocol["run"]["dt_s"]
        for n in range(protocol["run"]["steps"]):
            if variant["schedule"]=="step_reversal":
                qref=variant["sign"]*(.1 if n<400 else -.1)
                vref=0.
            else:
                qref=.1*math.sin(math.pi*n*dt)
                vref=.1*math.pi*math.cos(math.pi*n*dt)
            state.clear_forces()
            control.joint_f.zero_()
            control.joint_target_q.fill_(qref)
            control.joint_target_qd.fill_(vref)
            commands.append([float(control.joint_target_q.numpy()[0]),float(control.joint_target_qd.numpy()[0]),float(control.joint_f.numpy()[0])])
            start=time.perf_counter()
            solver.step(state,output,control=control,contacts=None,dt=dt)
            rows.append(snapshot(output,solver))
            elapsed.append(time.perf_counter()-start)
            state,output=output,state
        result["status"]="completed"
    except Exception as exc:
        result.update(status="failed",error=repr(exc))
        traceback.print_exc()
        exit_code=1
    finally:
        if rows:
            try:
                arrays={k:np.stack([r[k] for r in rows]) for k in rows[0]}
                arrays["t"]=np.arange(len(rows),dtype=np.float64)*protocol["run"]["dt_s"]
                arrays["command_q_v_f"]=np.asarray(commands,dtype=np.float64).reshape((-1,3))
                arrays["command_t"]=np.arange(len(commands),dtype=np.float64)*protocol["run"]["dt_s"]
                arrays["step_wall_s_including_export"]=np.asarray(elapsed)
                np.savez_compressed(out/"trajectory.npz",**arrays)
                result["samples"]=len(rows)
            except Exception as exc:
                result.update(status="failed",serialization_error=repr(exc));exit_code=1
                traceback.print_exc()
        result["finished_at_utc"]=datetime.now(timezone.utc).isoformat()
        sys.stdout.flush();sys.stderr.flush()
        sys.stdout,sys.stderr=old_stdout,old_stderr
        log.close()
        result["files_sha256"]={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!="result.json"}
        save(out/"result.json",result)
        print(json.dumps({"run_id":run_id,"status":result["status"]}))
    raise SystemExit(exit_code)
if __name__=="__main__": main()
