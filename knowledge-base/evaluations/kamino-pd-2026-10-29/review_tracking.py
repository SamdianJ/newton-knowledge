"""Read-only independent implicit 2x2-system reference for tracking publication."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
LAB=ROOT/"experiments/kamino_pd_lab/tracking"


def read(p):return json.loads(p.read_text(encoding="utf8"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mx(a):return float(np.max(np.abs(a)))


def main():
    p=read(LAB/"protocol.json");a=read(LAB/"analysis.json");checks=[];records=[];loaded={};rmss={}
    def ck(name,passed,actual=None):checks.append({"name":name,"passed":bool(passed),"actual":actual})
    for case in a["cases"]:
        spec=next(c for c in p["cases"] if c["id"]==case["id"])
        for variant in case["variants"]:
            label=variant["id"];vs=spec["variants"][label]
            for r in variant["runs"]:
                path=ROOT/r["run"];rr=read(path/"result.json");cfg=read(path/"resolved-config.json");z=dict(np.load(path/"trajectory.npz",allow_pickle=False));tag=r["run_id"]+"/"
                loaded[(case["id"],label,r["repeat"])]=z
                ck(tag+"archive hashes",all(sha(path/k)==v for k,v in rr["files_sha256"].items()))
                ck(tag+"frozen protocol and archived runner",sha(path/"protocol.json")==sha(LAB/"protocol.json")==r["protocol_sha256"] and sha(path/"runner.py")==r["program_sha256"])
                h=p["run"]["dt_s"];n=p["run"]["steps"];time=np.arange(n)*h
                ck(tag+"command-state time alignment",np.array_equal(z["command_t"],time) and np.array_equal(z["t"],np.arange(n+1)*h) and len(z["joint_q"])==n+1)
                if vs["schedule"]=="step_reversal":
                    qr=vs["sign"]*np.r_[np.full(400,.1),np.full(400,-.1)];vr=np.zeros(n)
                else:qr=.1*np.sin(np.pi*time);vr=.1*np.pi*np.cos(np.pi*time)
                commands=np.column_stack([qr,vr,np.zeros(n)])
                ck(tag+"independent commands",mx(z["command_q_v_f"]-commands)<2e-8)
                if vs["schedule"]=="sine":ck(tag+"nonzero velocity reference supplied",mx(z["command_q_v_f"][:,1])>.3)
                m=cfg["body_mass"][0];c=np.array(cfg["body_com"])[0];I=float(np.array(cfg["body_inertia"])[0,1,1]+m*(c[0]**2+c[2]**2));kp=cfg["joint_target_ke"][0];kd=cfg["joint_target_kd"][0]
                ck(tag+"model inertia and gains",I==1 and kp==25 and kd==10 and cfg["joint_effort_limit"]==[10.] and cfg["dof_act_paths"]==[2])
                state=np.zeros((n+1,2));tau=[]
                matrix=np.array([[1.,-h],[h*kp,I+h*kd]])
                for k in range(n):
                    use_v=vr[k] if vs["target_mode"]=="POSITION_VELOCITY" else 0.
                    rhs=np.array([state[k,0],I*state[k,1]+h*kp*qr[k]+h*kd*use_v])
                    state[k+1]=np.linalg.solve(matrix,rhs)
                    tau.append(I*(state[k+1,1]-state[k,1])/h)
                tau=np.array(tau);q=z["joint_q"][:,0];v=z["joint_qd"][:,0];actual=z["joint_lambdas_tau"][1:,0];wrench=z["applied_body_wrench"][1:,0,4]
                metrics={"joint_position_reference_max_abs_rad":mx(q-state[:,0]),"joint_velocity_reference_max_abs_rad_s":mx(v-state[:,1]),"reported_effort_reference_max_abs_Nm":mx(actual-tau),"applied_wrench_reference_max_abs_Nm":mx(wrench-tau),"reported_vs_applied_max_abs_Nm":mx(actual-wrench),"minimum_effort_margin_Nm":10-max(mx(actual),mx(wrench)),"reference_minimum_effort_margin_Nm":10-mx(tau)}
                for key,val in metrics.items():
                    gate=p["common_criteria"][key];ok=val>=gate if "margin" in key else val<=gate
                    ck(tag+key,ok,val)
                    ck(tag+"published metric "+key,np.isclose(val,r["metrics"][key],atol=1e-12,rtol=1e-6))
                full_rms=float(np.sqrt(np.mean((q[1:]-qr)**2)));ck(tag+"full RMS matches",abs(full_rms-r["metrics"]["full_tracking_rmse_rad"])<1e-12)
                if vs["schedule"]=="step_reversal":
                    increments=[]
                    # Frozen exclusion intentionally removes the target-jump pair 400 -> 401.
                    for indices,target in ((np.arange(0,401),vs["sign"]*.1),(np.arange(401,801),-vs["sign"]*.1)):
                        energy=.5*I*v[indices]**2+.5*kp*(q[indices]-target)**2
                        increments.extend(np.diff(energy))
                    e=max(0.,max(increments));ck(tag+"energy jump excluded frozen rule",e<=spec["criteria"]["segment_constant_target_energy_max_positive_increment_J"] and abs(e-r["metrics"]["segment_constant_target_energy_max_positive_increment_J"])<1e-12,e)
                    endpoint=mx(q[[400,800]]-qr[[399,799]]);ck(tag+"endpoint held-target alignment",endpoint<=spec["criteria"]["segment_end_error_max_abs_rad"] and abs(endpoint-r["metrics"]["segment_end_error_max_abs_rad"])<1e-12,endpoint)
                else:
                    rms=float(np.sqrt(np.mean((q[401:]-qr[400:])**2)));rmss[(label,r["repeat"])]=rms
                    ck(tag+"steady complete-period RMS",rms<=spec["criteria"]["steady_target_rmse_"+label+"_max_rad"] and abs(rms-r["metrics"]["steady_tracking_rmse_rad"])<1e-12,rms)
                    metrics["steady_RMS_rad"]=rms
                reported=np.column_stack([z["status_"+name][1:,0] for name in ("r_p","r_d","r_c")]);stop=(z["status_iterations"][1:,0]>1)&np.all(reported<=np.float32(1e-7),axis=1)
                ck(tag+"independent strict stop",np.array_equal(stop,z["status_converged"][1:,0].astype(bool)) and np.mean(stop)==r["solver_diagnostics"]["converged_fraction"])
                records.append({"run_id":r["run_id"],"case":case["id"],"variant":label,"repeat":r["repeat"],"independent_metrics":metrics,"strict_fraction":float(np.mean(stop))})
        for label in ("A","B"):
            for field in ("body_q","body_qd","joint_q","joint_qd"):
                aa=loaded[(case["id"],label,1)][field];bb=loaded[(case["id"],label,2)][field]
                atol=p["run"]["repeat_tolerance"]["velocity_atol" if field.endswith("qd") else "pose_atol"]
                ck(case["id"]+" repeat "+label+" "+field,np.allclose(aa,bb,atol=atol,rtol=1e-5),mx(aa-bb))
        if case["id"].endswith("step_reversal"):
            for repeat in (1,2):
                for field,gate in (("joint_q",spec["criteria"]["mirrored_q_max_abs_sum_rad"]),("joint_qd",spec["criteria"]["mirrored_v_max_abs_sum_rad_s"])):
                    err=mx(loaded[(case["id"],"A",repeat)][field]+loaded[(case["id"],"B",repeat)][field]);ck("mirror"+str(repeat)+field,err<=gate,err)
        else:
            for repeat in (1,2):
                improvement=1-rmss[("A",repeat)]/rmss[("B",repeat)];ck("RMS improvement "+str(repeat),improvement>=spec["criteria"]["steady_rmse_relative_improvement_A_min"],improvement)
    ck("eight formal runs",len(records)==8 and a["formal_runs"]==8)
    findings=[]
    report={"status":"passed" if all(c["passed"] for c in checks) else "failed","checks_total":len(checks),"checks_passed":sum(c["passed"] for c in checks),"checks":checks,"runs":records,"findings":findings,"source_semantics":{"equation":"Solve [1,-h;h*kp,I+h*kd] [q_next,v_next] = [q,I*v+h*kp*qref+h*kd*vref_used]. Interior bounded-row optimality plus Euler integration; no clipping in the reference, separately certified by >=4Nm margin.","POSITION":"target_qd is ignored as a reference, while kd still contributes damping. Source kinematics/joints.py:1033-1054 and core/joints.py:1999.","sampling":"State[n+1] follows command[n] at n*dt; final period uses state401..800 with commands400..799.","energy":"Both fixed-target segments independently evaluated; no cross-jump energy term, and pair400->401 is excluded exactly as preregistered."},"scope":"Independent saved-data and static-source review, without importing subgroup analyzer or executing physics.","limitations":["One gain, inertia, frequency and time step; CPU single rotor interior response only.","Preconditioning field in frozen protocol has a constraints label but runner documents mapping to actual dynamics.preconditioning and archives resolved values.","Successful convergence here does not resolve old saturated high-gain/offset-COM failure."],"evidence_sha256":{str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in [LAB/"analysis.json",LAB/"protocol.json",LAB/"runner.py",Path(__file__)]}}
    (Path(__file__).parent/"review-tracking.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":report["status"],"checks":len(checks),"failed":[c for c in checks if not c["passed"]]}))


if __name__=="__main__":main()
