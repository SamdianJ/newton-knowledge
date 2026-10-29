"""Independent float64 scalar dynamics reference and frozen acceptance checks."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/"manifests/source-lock.json").exists())
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def mx(v): return float(np.max(np.abs(v))) if np.size(v) else 0.

def reference(protocol, variant, cfg):
    """Independent command generation + scalar recurrence; never calls Newton."""
    h=protocol["run"]["dt_s"]
    steps=protocol["run"]["steps"]
    com=np.asarray(cfg["body_com"])[0]
    inertia=float(np.asarray(cfg["body_inertia"])[0,1,1]+cfg["body_mass"][0]*(com[0]**2+com[2]**2))
    kp=float(cfg["joint_target_ke"][0]);kd=float(cfg["joint_target_kd"][0])
    q=np.zeros(steps+1);v=np.zeros(steps+1);tau=np.zeros(steps)
    command=np.zeros((steps,3))
    for n in range(steps):
        if variant["schedule"]=="step_reversal":
            command[n,0]=variant["sign"]*(.1 if n<400 else -.1)
        else:
            command[n,0]=.1*np.sin(np.pi*n*h)
            command[n,1]=.1*np.pi*np.cos(np.pi*n*h)
        used=command[n,1] if variant["target_mode"]=="POSITION_VELOCITY" else 0.
        v[n+1]=(inertia*v[n]+h*(kp*(command[n,0]-q[n])+kd*used))/(inertia+h*kd+h*h*kp)
        q[n+1]=q[n]+h*v[n+1]
        tau[n]=inertia*(v[n+1]-v[n])/h
    return {"joint_q":q,"joint_qd":v,"effort_Nm":tau,"command_q_v_f":command,"I":np.asarray(inertia)}

def plot(case, entries, arrays, refs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams["svg.hashsalt"]="kamino-pd-tracking-v1"
    fig,axes=plt.subplots(2,2,figsize=(12,7),constrained_layout=True)
    for variant in ("A","B"):
        d=arrays[(variant,1)]; ref=refs[(variant,1)];t=d["t"]
        label=variant+" "+case["variants"][variant]["target_mode"]
        color="tab:blue" if variant=="A" else "tab:orange"
        axes[0,0].plot(t,d["joint_q"][:,0],label=label,color=color)
        axes[0,0].plot(t,ref["joint_q"],linestyle=":",alpha=.65,color=color)
        axes[0,1].plot(t,d["joint_qd"][:,0],label=label,color=color)
        axes[1,0].plot(t[1:],d["joint_lambdas_tau"][1:,0],label=label,color=color)
        axes[1,1].plot(t,np.abs(d["joint_q"][:,0]-ref["joint_q"]),label=label,color=color)
    axes[0,0].plot(arrays[("A",1)]["command_t"],refs[("A",1)]["command_q_v_f"][:,0],color="black",alpha=.4,linestyle="--",label="A target")
    for ax,ylabel in zip(axes.flat,["Angle [rad]; dotted = independent reference","Velocity [rad/s]","Reported torque [N m]; limit = +/-10","Absolute angle-reference error [rad]"]):
        ax.set_xlabel("Time [s]");ax.set_ylabel(ylabel);ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.suptitle(case["id"]+" | repeat 1; frozen criteria evaluated for both repeats")
    name=case["id"]+".svg"
    fig.savefig(HERE/name,metadata={"Date":None})
    fig.savefig(HERE/(case["id"]+".png"),dpi=140)
    plt.close(fig)
    return "tracking/"+name

def main():
    protocol=load(HERE/"protocol.json")
    ph,rh=sha(HERE/"protocol.json"),sha(HERE/"runner.py")
    selected=[];excluded=[]
    for p in sorted((HERE/"runs").glob("*/result.json")):
        r=load(p);r["path"]=p.parent
        if r["status"]=="completed" and r["protocol_sha256"]==ph and r["runner_sha256"]==rh: selected.append(r)
        else: excluded.append({"run_id":r["run_id"],"status":r["status"],"reason":r.get("error","different protocol/runner"),"runner_sha256":r["runner_sha256"]})
    cases=[];all_checks=[]
    for case in protocol["cases"]:
        variants=[];arrays={};refs={};case_checks=[]
        for variant,spec in case["variants"].items():
            runs=sorted([r for r in selected if r["case"]==case["id"] and r["variant"]==variant],key=lambda r:r["repeat"])
            if len(runs)!=2 or [r["repeat"] for r in runs]!=[1,2]: raise ValueError("Must have exactly independent repeats 1,2 per setting; preserve failures and review cohort explicitly")
            outputs=[]
            for r in runs:
                p=r["path"];d=dict(np.load(p/"trajectory.npz",allow_pickle=False));cfg=load(p/"resolved-config.json")
                arrays[(variant,r["repeat"])]=d
                ref=reference(protocol,spec,cfg);refs[(variant,r["repeat"])]=ref
                np.savez_compressed(HERE/(r["run_id"]+"-reference.npz"),**ref)
                checks=[];metrics={}
                def check(name,passed,actual=None,expected=None): checks.append({"name":name,"passed":bool(passed),"actual":actual,"expected":expected})
                def upper(name,value):
                    lim=protocol["common_criteria"].get(name,case["criteria"].get(name));metrics[name]=float(value);check(name,value<=lim,float(value),{"max":lim})
                def lower(name,value):
                    lim=protocol["common_criteria"].get(name,case["criteria"].get(name));metrics[name]=float(value);check(name,value>=lim,float(value),{"min":lim})
                check("archive_hashes",all(sha(p/k)==v for k,v in r["files_sha256"].items()))
                source=load(p/"installed-source-validation.json")
                check("installed_source_809",source["checked_python_files"]==809 and not source["missing"] and not source["changed"])
                check("sample_counts",len(d["t"])==801 and d["command_q_v_f"].shape==(800,3))
                check("finite_physical_and_poststep_status",all(np.isfinite(v[1:] if k.startswith("status_") else v).all() for k,v in d.items()))
                check("frozen_model",cfg["body_mass"]==[1.] and np.array_equal(cfg["body_inertia"],[np.eye(3)]) and np.array_equal(cfg["body_com"],[[0,0,0]]) and cfg["joint_target_ke"]==[25.] and cfg["joint_target_kd"]==[10.] and cfg["joint_effort_limit"]==[10.])
                solver_matches=True
                for setting,value in protocol["solver"].items():
                    api_setting="dynamics" if setting=="constraints" else setting
                    actual=cfg["solver"][api_setting]
                    solver_matches &= all(actual[k]==v for k,v in value.items()) if isinstance(value,dict) else actual==value
                check("frozen_solver_actual_values",solver_matches)
                check("actual_drive_path",cfg["dof_act_paths"]==[2],cfg["dof_act_paths"],[2])
                check("command_schedule",mx(d["command_q_v_f"]-ref["command_q_v_f"])<2e-8)
                q=d["joint_q"][:,0];v=d["joint_qd"][:,0];tau=d["joint_lambdas_tau"][1:,0];applied=d["applied_body_wrench"][1:,0,4]
                upper("joint_position_reference_max_abs_rad",mx(q-ref["joint_q"]))
                upper("joint_velocity_reference_max_abs_rad_s",mx(v-ref["joint_qd"]))
                upper("reported_effort_reference_max_abs_Nm",mx(tau-ref["effort_Nm"]))
                upper("applied_wrench_reference_max_abs_Nm",mx(applied-ref["effort_Nm"]))
                upper("reported_vs_applied_max_abs_Nm",mx(tau-applied))
                lower("minimum_effort_margin_Nm",10-max(mx(tau),mx(applied)))
                lower("reference_minimum_effort_margin_Nm",10-mx(ref["effort_Nm"]))
                upper("joint_anchor_origin_max_norm_m",float(np.linalg.norm(d["body_q"][:,0,:3],axis=1).max()))
                body_angle=2*np.arctan2(d["body_q"][:,0,4],d["body_q"][:,0,6])
                upper("joint_vs_body_angle_max_abs_rad",mx(q-body_angle))
                upper("body_quaternion_norm_max_abs_error",mx(np.linalg.norm(d["body_q"][:,0,3:],axis=1)-1))
                upper("joint_position_max_abs_rad",mx(q));upper("joint_velocity_max_abs_rad_s",mx(v))
                metrics["full_tracking_rmse_rad"]=float(np.sqrt(np.mean((q[1:]-ref["command_q_v_f"][:,0])**2)))
                metrics["full_tracking_peak_error_rad"]=mx(q[1:]-ref["command_q_v_f"][:,0])
                if spec["schedule"]=="step_reversal":
                    upper("segment_end_error_max_abs_rad",mx(q[[400,800]]-ref["command_q_v_f"][[399,799],0]))
                    upper("segment_end_velocity_max_abs_rad_s",mx(v[[400,800]]))
                    energy_diffs=[]
                    for start,end,target in ((0,400,spec["sign"]*.1),(401,800,-spec["sign"]*.1)):
                        energy=.5*v[start:end+1]**2+.5*25*(q[start:end+1]-target)**2
                        energy_diffs.extend(np.diff(energy))
                    upper("segment_constant_target_energy_max_positive_increment_J",max(0.,float(max(energy_diffs))))
                else:
                    rms=float(np.sqrt(np.mean((q[401:]-ref["command_q_v_f"][400:,0])**2)))
                    metrics["steady_tracking_rmse_rad"]=rms
                    upper("steady_target_rmse_"+variant+"_max_rad",rms)
                status={"converged_fraction":float(d["status_converged"][1:].mean()),"all_steps_converged":bool(d["status_converged"][1:].all()),"iterations_max":int(d["status_iterations"][1:].max()),"iterations_mean":float(d["status_iterations"][1:].mean()),"residual_max":{k:mx(d["status_"+k][1:]) for k in ("r_p","r_d","r_c")},"residual_final":{k:float(d["status_"+k][-1,0]) for k in ("r_p","r_d","r_c")}}
                values,counts=np.unique(d["status_iterations"][1:],return_counts=True)
                status["iteration_distribution"]={str(int(value)):int(count) for value,count in zip(values,counts)}
                outputs.append({"run_id":r["run_id"],"run":p.relative_to(ROOT).as_posix(),"repeat":r["repeat"],"status":"passed" if all(c["passed"] for c in checks) else "failed_criteria","metrics":metrics,"solver_diagnostics":status,"checks":checks,"raw_file":(p/"trajectory.npz").relative_to(ROOT).as_posix(),"raw_sha256":sha(p/"trajectory.npz"),"program_sha256":rh,"protocol_sha256":ph,"config":cfg,"result_file":(p/"result.json").relative_to(ROOT).as_posix()})
                all_checks+=checks
            repeat=[]
            for f in ("body_q","body_qd","joint_q","joint_qd"):
                a,b=arrays[(variant,1)][f],arrays[(variant,2)][f]
                tol=protocol["run"]["repeat_tolerance"]
                at=tol["velocity_atol"] if f.endswith("qd") else tol["pose_atol"]
                repeat.append({"name":"repeat_"+f,"passed":bool(np.allclose(a,b,atol=at,rtol=tol["rtol"])),"max_abs":mx(a-b)})
            all_checks+=repeat
            variants.append({"id":variant,"runs":outputs,"repeat_checks":repeat})
        for rep in (1,2):
            if case["id"].endswith("step_reversal"):
                for field,name in (("joint_q","mirrored_q_max_abs_sum_rad"),("joint_qd","mirrored_v_max_abs_sum_rad_s")):
                    value=mx(arrays[("A",rep)][field]+arrays[("B",rep)][field])
                    case_checks.append({"name":name,"repeat":rep,"actual":value,"max":case["criteria"][name],"passed":value<=case["criteria"][name]})
            else:
                a,b=[next(v for v in variants if v["id"]==label)["runs"][rep-1]["metrics"]["steady_tracking_rmse_rad"] for label in ("A","B")]
                value=1-a/b
                case_checks.append({"name":"steady_rmse_relative_improvement_A_min","repeat":rep,"actual":value,"min":.3,"passed":value>=.3})
        all_checks+=case_checks
        passed=all(r["status"]=="passed" for v in variants for r in v["runs"]) and all(c["passed"] for c in case_checks) and all(c["passed"] for v in variants for c in v["repeat_checks"])
        cases.append({"id":case["id"],"title":case["title"],"status":"passed" if passed else "failed_criteria","variants":variants,"paired_checks":case_checks,"criteria":{**protocol["common_criteria"],**case["criteria"]},"limitations":protocol["limitations"]+case["limitations"],"source_refs":protocol["source_refs"],"plot":plot(case,variants,arrays,refs)})
    result={"status":"passed" if all(c["status"]=="passed" for c in cases) else "completed_with_failed_criteria","protocol_sha256":ph,"runner_sha256":rh,"analyzer_sha256":sha(Path(__file__)),"formal_runs":len(selected),"passed_checks":sum(c["passed"] for c in all_checks),"failed_checks":sum(not c["passed"] for c in all_checks),"cases":cases,"excluded_runs":excluded,"acceptance_scope":"Physical acceptance only; strict solver-convergence flags are independently reported and never inferred from physical agreement."}
    save(HERE/"analysis.json",result)
    print(json.dumps({k:result[k] for k in ("status","formal_runs","passed_checks","failed_checks")}))
if __name__=="__main__": main()
