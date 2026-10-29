"""Independent saved-data review. Does not import the experiment analyzer or Newton."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
LAB=ROOT/"experiments/kamino_pd_lab/limit_switch"


def read(p):return json.loads(p.read_text(encoding="utf8"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    protocol=read(LAB/"protocol.json");g=protocol["criteria"];checks=[];records=[];raw={}
    def ck(name,ok,actual=None):checks.append({"name":name,"passed":bool(ok),"actual":actual})
    for rf in sorted(LAB.glob("runs/*/result.json")):
        r=read(rf);path=rf.parent
        if r["status"]!="completed":continue
        v=r["variant"];events=read(path/"events.json");cfg=read(path/"resolved-config.json")
        z=dict(np.load(path/"trajectory.npz",allow_pickle=False));raw[(v,r["repeat"])]=z
        tag=path.name+"/"
        ck(tag+"hashes",all(sha(path/k)==h for k,h in r["files_sha256"].items()))
        ck(tag+"archived protocol and runner",sha(path/"protocol.json")==sha(LAB/"protocol.json")==r["protocol_sha256"] and sha(path/"runner.py")==r["runner_sha256"])
        ck(tag+"physical model inertia",cfg["body_mass"]==[1.] and cfg["body_com"]==[[0.,0.,0.]] and np.array_equal(cfg["body_inertia"],np.eye(3)[None]))
        h=protocol["run"]["dt_s"];kp=protocol["scene"]["kp_Nm_per_rad"];kd=protocol["scene"]["kd_Nms_per_rad"]
        q=np.zeros(121);vel=np.zeros(121);torque=[];free=[]
        limits=np.repeat(protocol["case"]["variants"][v]["limits_Nm"],20)
        targets=np.repeat(protocol["run"]["target_q_rad"],20)
        for k in range(120):
            # Solve the implicit scalar velocity equation, then apply torque bounds.
            unconstrained_next_v=(vel[k]/h+kp*(targets[k]-q[k]))/(1/h+kd+h*kp)
            raw_tau=(unconstrained_next_v-vel[k])/h
            tau=min(limits[k],max(-limits[k],raw_tau));free.append(raw_tau);torque.append(tau)
            vel[k+1]=vel[k]+h*tau;q[k+1]=q[k]+h*vel[k+1]
        torque=np.array(torque);free=np.array(free);measured=z["joint_lambdas_tau"][1:,0];wrench=z["applied_body_wrench"][1:,0,4]
        errs={"effort":float(np.max(abs(measured-torque))),"q":float(np.max(abs(z["joint_q"][:,0]-q))),"qd":float(np.max(abs(z["joint_qd"][:,0]-vel)))}
        ck(tag+"independent scalar reference",errs["effort"]<=g["effort_reference_Nm"] and errs["q"]<=g["angle_reference_rad"] and errs["qd"]<=g["speed_reference_rad_s"],errs)
        ck(tag+"wrench same reference",np.max(abs(wrench-torque))<=g["effort_reference_Nm"])
        ck(tag+"actual current limits",np.array_equal(z["step_model_limit_after_step"][:,0],limits) and np.array_equal(z["step_command_limit"],limits))
        ck(tag+"same-step impulse bound",np.max(abs(z["step_bound_after_step"][:,0]-h*limits))<=g["bound_impulse_error_Nms"])
        expected=[20,40,80,100] if v=="A" else []
        notified=[e["step_index"] for e in events if e["notify_called"]]
        ck(tag+"exact notify edges",notified==expected,notified)
        ck(tag+"public notify precedes control and step",all(e["sequence"]==["model_fill","notify","control","step"] for e in events if e["notify_called"]))
        ck(tag+"notification state invariance",all(max(e["notify_state_max_abs"].values())<=g["notify_state_change"] for e in events))
        ck(tag+"bounded row retained",all(e["path_before"]==e["path_after"]==e["path_after_step"]==[2] and e["effort_row_count"]==1 for e in events))
        first=[]
        for k in expected:
            err=float(abs(measured[k]-torque[k]));first.append({"step":k,"actual_Nm":float(measured[k]),"reference_Nm":float(torque[k]),"error_Nm":err,"limit_Nm":float(limits[k])})
            ck(tag+"first post-notify step "+str(k),err<=g["effort_reference_Nm"])
        branches=[]
        for phase in range(6):
            sl=slice(phase*20,(phase+1)*20);sgn=1 if phase<3 else -1
            saturated=(phase not in (1,4)) or v=="B"
            if saturated:
                good=np.all(sgn*free[sl]>limits[sl]) and np.max(abs(measured[sl]-sgn*limits[sl]))<=g["effort_reference_Nm"]
                value=float(np.max(abs(measured[sl]-sgn*limits[sl])))
            else:
                value=float(np.min(limits[sl]-abs(measured[sl])));good=value>=g["unsaturated_margin_Nm"] and np.all(sgn*measured[sl]>0)
            ck(tag+"all20 branch phase"+str(phase),good,value);branches.append({"phase":phase,"saturated":saturated,"value":value})
        rr=np.column_stack([z["status_"+n][1:,0] for n in ("r_p","r_d","r_c")]);it=z["status_iterations"][1:,0]
        independently_converged=(it>1)&np.all(rr<=np.float32(1e-7),axis=1)
        ck(tag+"strict status independently consistent",np.array_equal(independently_converged,z["status_converged"][1:,0].astype(bool)) and independently_converged.all())
        ck(tag+"solved status finite",np.isfinite(rr).all())
        records.append({"run_id":path.name,"variant":v,"repeat":r["repeat"],"reference_errors":errs,"first_post_notify_steps":first,"branches":branches,"strict_fraction":float(independently_converged.mean())})
    ck("four unique runs",len(raw)==4 and len(records)==4)
    for v in ("A","B"):
        for field in ("body_q","body_qd","joint_q","joint_qd","joint_lambdas_tau"):
            ck("exact independent repeat "+v+"/"+field,np.array_equal(raw[(v,1)][field],raw[(v,2)][field]))
    runner=(LAB/"runner.py").read_text(encoding="utf8")
    ck("static public notification API present","solver.notify_model_changed(newton.ModelFlags.JOINT_DOF_FORCE_PROPERTIES)" in runner)
    ck("static snapshots copy arrays","numpy().copy()" in runner and 'old_limit = model.joint_effort_limit.numpy().copy()' in runner)
    report={"status":"passed" if all(c["passed"] for c in checks) else "failed","checks_passed":sum(c["passed"] for c in checks),"checks_total":len(checks),"checks":checks,"runs":records,"findings":[],"scope":"Independent raw-array scalar reference, notification order, current bounds, first-step effects, actual saturation branches and strict-status checks. No simulation rerun or group-file modification.","limitations":["Finite-positive .25/4 Nm updates preserve one bounded row; no zero/inf or unnotified-update contract tested.","State invariance across notify is supported by copied event diagnostics and static runner inspection; complete before/after notification states were not separately saved.","This smaller drive converges under strict tolerances; that does not resolve the high-gain/offset-COM saturation case."],"evidence_sha256":{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [LAB/"analysis.json",LAB/"protocol.json",LAB/"runner.py",Path(__file__)]}}
    (Path(__file__).parent/"review-limit-switch.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":report["status"],"checks":len(checks),"failed":[c for c in checks if not c["passed"]]}))


if __name__=="__main__":main()
