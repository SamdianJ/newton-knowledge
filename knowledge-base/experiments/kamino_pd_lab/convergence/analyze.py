"""Independent frozen-gate analysis of saved PD trajectories and iteration exports."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(p):
    return json.loads(Path(p).read_text(encoding="utf8"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return Path(p).relative_to(ROOT).as_posix()


def save(p, x):
    Path(p).write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf8")


def check(checks, name, passed, actual=None, expected=None):
    checks.append({"name":name,"passed":bool(passed),"actual":actual,"expected":expected})


def flat(d, prefix=""):
    out = {}
    for k,v in d.items():
        key = prefix+k
        if isinstance(v,dict):out.update(flat(v,key+"."))
        else:out[key] = v
    return out


def load_active(path):
    with np.load(path, allow_pickle=False) as z:
        count = int(z["dim"][0,0])
        result = {}
        vectors = {"x","y","z","pre_x_p","pre_y_input","pre_z_input","P"}
        for k in z.files:
            a = z[k]
            result[k] = a[:,:count].copy() if k in vectors else a.copy()
        if "allocated_capacity" not in result:
            result["allocated_capacity"] = np.full(len(result["outer_step"]), z["x"].shape[1])
    return result


def reconstruct(i, dtype):
    x,y,z,P = [i[k].astype(dtype) for k in ("x","y","z","P")]
    xp,yp = i["pre_x_p"].astype(dtype),i["pre_y_input"].astype(dtype)
    eta,rho = i["eta"].astype(dtype),i["rho"].astype(dtype)
    rp = np.max(np.abs(P*(x-y)),axis=1)
    t1,t2 = eta*(x-xp),rho*(y-yp)
    rd = np.max(np.abs((t1+t2)/P),axis=1)
    b=int(i["bcgo"][0,0]);lo=i["bound_lower"][:,0].astype(dtype);hi=i["bound_upper"][:,0].astype(dtype)
    c1=(x[:,b]-lo)*np.maximum(z[:,b],0)
    c2=(hi-x[:,b])*np.maximum(-z[:,b],0)
    rc=np.abs(c1+c2)
    eps=np.finfo(np.float32).eps
    bounds=np.column_stack([64*eps*np.max(P*(np.abs(x)+np.abs(y)),axis=1)+1e-12,64*eps*np.max((np.abs(t1)+np.abs(t2))/P,axis=1)+1e-12,64*eps*(np.abs(c1)+np.abs(c2))+1e-12])
    return np.column_stack([rp,rd,rc]),bounds


def run_analysis(path, protocol):
    r=read(path/"result.json");checks=[];physical=[]
    check(checks,"archived file hashes",all(sha(path/k)==h for k,h in r["files_sha256"].items()))
    check(checks,"frozen protocol",sha(path/"protocol.json")==sha(HERE/"protocol.json")==r["protocol_sha256"])
    check(checks,"archived runner",sha(path/"runner.py")==r["runner_sha256"])
    validation=read(path/"installed-source-validation.json")
    check(checks,"installed locked Python sources",not validation["missing"] and not validation["changed"],validation["checked_python_files"])
    with np.load(path/"trajectory.npz",allow_pickle=False) as z:
        t={k:z[k].copy() for k in z.files}
    i=load_active(path/"iterations.npz")
    for k,a in t.items():
        defined=a[1:] if k.startswith("status_") and k!="status_defined" else a
        check(checks,"finite trajectory "+k,np.isfinite(defined).all())
    check(checks,"finite active iteration arrays",all(np.isfinite(a).all() for a in i.values()))
    check(checks,"six active rows one bounded row",np.all(i["dim"]==6) and np.all(i["nbc"]==1) and np.all(i["vio"]==0))
    check(checks,"81 physical samples",len(t["t"])==81 and np.array_equal(t["time"],t["t"]))
    calc,bounds=reconstruct(i,np.float64);calc32,_=reconstruct(i,np.float32)
    reported=np.column_stack([i["status_"+k][:,0] for k in ("r_p","r_d","r_c")])
    err=np.abs(calc-reported)
    check(checks,"independent residual reconstruction",np.all(err<=bounds),{"max_abs_errors":err.max(axis=0).tolist(),"max_roundoff_ratio":np.max(err/bounds,axis=0).tolist()},"all iterations inside frozen 64*eps expression bound+1e-12")
    cfg=read(path/"resolved-config.json");pc=cfg["solver"]["padmm"]
    eps=np.array([pc[k] for k in ("primal_tolerance","dual_tolerance","compl_tolerance")],dtype=np.float32)
    stop=(i["status_iterations"][:,0]>1)&np.all(reported<=eps,axis=1)
    check(checks,"independent reported stop Boolean",np.array_equal(stop,i["status_converged"][:,0].astype(bool)))
    terminal=[]
    for step in range(80):
        idx=np.flatnonzero(i["outer_step"]==step);terminal.append(int(idx[-1]))
        check(checks,"iteration count step "+str(step),len(idx)==int(t["status_iterations"][step+1,0]) and np.array_equal(i["status_iterations"][idx,0],np.arange(1,len(idx)+1)))
        check(checks,"terminal snapshot step "+str(step),all(i["status_"+k][idx[-1],0]==t["status_"+k][step+1,0] for k in ("converged","iterations","r_p","r_d","r_c")))
    terminal=np.array(terminal)
    strict=np.all(reported[terminal]<=np.float32(1e-7),axis=1)&(i["status_iterations"][terminal,0]>1)
    strict_calc=np.all(calc[terminal]<=float(np.float32(1e-7)),axis=1)
    np.savez_compressed(path.parent.parent/"derived"/(path.name+"-residuals.npz"),outer_step=i["outer_step"],iteration=i["status_iterations"][:,0],recomputed_float64=calc,recomputed_float32=calc32,reported=reported,roundoff_allowance=bounds,terminal_indices=terminal,configured_stop=stop,strict_terminal_stop=strict)
    dt=protocol["common_run"]["dt_s"]
    tau=np.r_[np.ones(40),-np.ones(40)];v=np.r_[0,np.cumsum(tau*dt/1.25)];q=np.r_[0,np.cumsum(v[1:]*dt)]
    metrics={"joint_velocity_reference_max_abs_rad_s":float(np.max(np.abs(t["joint_qd"][:,0]-v))),"joint_position_euler_reference_max_abs_rad":float(np.max(np.abs(t["joint_q"][:,0]-q))),"applied_effort_signed_max_abs_error_Nm":float(np.max(np.abs(t["applied_body_wrench"][1:,0,4]-tau))),"applied_effort_max_Nm":float(np.max(np.abs(t["applied_body_wrench"][1:,0,4]))),"joint_anchor_origin_max_norm_m":float(np.max(np.linalg.norm(t["body_q"][:,0,:3],axis=1))),"bounded_reported_effort_max_error_Nm":float(np.max(np.abs(t["joint_lambdas_tau"][1:,0]-tau))),"configured_converged_fraction":float(np.mean(t["status_converged"][1:])) ,"strict_converged_fraction":float(np.mean(strict)),"independently_reconstructed_strict_fraction":float(np.mean(strict_calc)),"iterations_max":int(t["status_iterations"][1:].max()),"terminal_rp_median":float(np.median(t["status_r_p"][1:])),"terminal_rd_median":float(np.median(t["status_r_d"][1:])),"terminal_rc_median_J":float(np.median(t["status_r_c"][1:])),"terminal_rc_min_J":float(t["status_r_c"][1:].min()),"terminal_rc_max_J":float(t["status_r_c"][1:].max())}
    for name,gate in protocol["physical_criteria"].items():
        actual=cfg["dof_act_paths"] if name=="routing" else metrics[name]
        check(physical,name,actual==gate if name=="routing" else actual<=gate,actual,gate)
    if r["variant"]=="baseline":
        with np.load(ROOT/protocol["legacy_baselines"][r["repeat"]-1]/"trajectory.npz") as legacy:
            for k in ("body_q","body_qd","joint_q","joint_qd"):
                atol=1e-4 if k.endswith("qd") else 1e-5
                check(checks,"legacy observer invariance "+k,np.allclose(t[k],legacy[k],atol=atol,rtol=1e-5),float(np.max(np.abs(t[k]-legacy[k]))),atol)
        check(checks,"legacy status reproduced",np.all(t["status_converged"][1:]==0) and np.all(t["status_iterations"][1:]==200))
    diagnostics=[];b=int(i["bcgo"][0,0])
    for step in (0,1,39,40,41,79):
        ids=np.flatnonzero(i["outer_step"]==step)[-20:];end=ids[-1]
        x,y,z=[i[k][end,b] for k in ("x","y","z")]
        bound=i["bound_lower"][end,0] if z>0 else i["bound_upper"][end,0]
        correction=float(i["rho"][end,0])*float(y-x)
        half_ulp_z=.5*abs(float(np.spacing(z)))
        pre_z=i["pre_z_input"][end,b]
        rc=reported[ids,2];state=np.concatenate([i[k][ids] for k in ("x","y","z")],axis=1)
        diagnostics.append({"outer_step":step,"terminal_iteration":int(i["status_iterations"][end,0]),"tail_count":len(ids),"tail20_rc_range_J":[float(rc.min()),float(rc.max())],"tail20_relative_span":float(np.ptp(rc)/max(np.max(np.abs(rc)),1e-30)),"tail20_unique_complete_states":len(np.unique(state,axis=0)),"tail20_unique_bounded_states":len(np.unique(np.column_stack([i[k][ids,b] for k in ("x","y","z")]),axis=0)),"bounded_x":float(x),"bounded_y":float(y),"bounded_z":float(z),"pre_z_input":float(pre_z),"actual_z_change":float(z-pre_z),"float32_add_loses_increment":bool(np.float32(pre_z+np.float32(correction))==pre_z and correction!=0),"complementary_bound":float(bound),"gap_x_to_bound":float(abs(x-bound)),"gap_in_bound_ULPs":float(abs(float(x)-float(bound))/abs(float(np.spacing(bound)))),"dual_update_rho_y_minus_x":correction,"half_ULP_z":half_ulp_z,"dual_update_below_half_ULP":bool(abs(correction)<half_ulp_z),"recomputed_product_J":float(calc[end,2]),"projected_y_equals_bound":bool(y==bound),"preconditioner_P":float(i["P"][end,b])})
    return {"run":rel(path),"run_id":path.name,"variant":r["variant"],"repeat":r["repeat"],"status":"passed" if all(c["passed"] for c in checks) else "evidence_failed","physical_acceptance":"passed" if all(c["passed"] for c in physical) else "failed_criteria","checks":checks,"physical_criteria":physical,"metrics":metrics,"diagnostics":diagnostics,"raw_file":rel(path/"trajectory.npz"),"raw_sha256":sha(path/"trajectory.npz"),"iteration_file":rel(path/"iterations.npz"),"iteration_sha256":sha(path/"iterations.npz"),"program_sha256":r["runner_sha256"],"protocol_sha256":r["protocol_sha256"],"allocated_capacity":int(i["allocated_capacity"][0]),"exported_active_columns":6},t,i,cfg


def main():
    p=read(HERE/"protocol.json");(HERE/"derived").mkdir(exist_ok=True)
    records=[];excluded=[];loaded={};configs={};global_checks=[]
    for file in sorted(HERE.glob("runs/*/result.json")):
        result=read(file)
        if result["status"]!="completed":
            excluded.append({"run":rel(file.parent),"classification":"harness_failed","error":result.get("error")});continue
        rec,t,i,cfg=run_analysis(file.parent,p)
        records.append(rec);loaded[(rec["variant"],rec["repeat"])]=(t,i);configs[(rec["variant"],rec["repeat"])]=cfg
    check(global_checks,"10 unique formal variant/repeat runs",len(records)==10 and len(loaded)==10)
    for variant in p["variants"]:
        if (variant,1) not in loaded or (variant,2) not in loaded:continue
        a,b=loaded[(variant,1)],loaded[(variant,2)]
        for field in ("body_q","body_qd","joint_q","joint_qd"):
            atol=1e-4 if field.endswith("qd") else 1e-5
            check(global_checks,"independent repeat "+variant+"/"+field,np.allclose(a[0][field],b[0][field],atol=atol,rtol=1e-5),float(np.max(np.abs(a[0][field]-b[0][field]))),{"atol":atol,"rtol":1e-5})
        for field in ("x","y","z","pre_x_p","pre_y_input","pre_z_input","status_converged","status_iterations","status_r_p","status_r_d","status_r_c"):
            same=a[1][field].shape==b[1][field].shape and np.array_equal(a[1][field],b[1][field])
            check(global_checks,"active iteration repeat "+variant+"/"+field,same)
        base=flat(configs[("baseline",1)]["solver"]);other=flat(configs[(variant,1)]["solver"])
        changed={k:{"baseline":base[k],"treatment":other[k]} for k in base if base[k]!=other[k]}
        check(global_checks,"exact single-factor diff "+variant,set(changed)==set(p["variants"][variant]["overrides"]),changed,p["variants"][variant]["overrides"])
    status="passed" if all(c["passed"] for c in global_checks) and all(r["status"]=="passed" for r in records) else "incomplete_or_evidence_failed"
    comparisons=[]
    for c in p["pair_cases"]:
        if (c["A"],1) not in loaded or (c["B"],1) not in loaded:continue
        ta,tb=loaded[(c["A"],1)][0],loaded[(c["B"],1)][0]
        comparisons.append({"id":c["id"],"A":c["A"],"B":c["B"],"max_absolute_differences":{k:float(np.max(np.abs(ta[k][1:]-tb[k][1:]))) for k in ("body_q","body_qd","joint_q","joint_qd","status_r_p","status_r_d","status_r_c")}})
    output={"status":status,"analyzer_sha256":sha(__file__),"protocol_sha256":sha(HERE/"protocol.json"),"formal_runs":len(records),"runs":records,"comparisons":comparisons,"checks":global_checks,"excluded_runs":excluded,"source_refs":p["source_refs"],"limitations":p["limitations"],"note":"Evidence status is separate from physical acceptance and configured/strict convergence. Active-only exports normalize valid full-capacity baseline to six active rows; archived programs need not share hashes."}
    save(HERE/"analysis.json",output)
    print(json.dumps({"status":status,"formal_runs":len(records),"failed_checks":[c["name"] for c in global_checks if not c["passed"]],"runs":[{"variant":r["variant"],"repeat":r["repeat"],"status":r["status"],"physical":r["physical_acceptance"],"metrics":r["metrics"]} for r in records]},ensure_ascii=False))


if __name__=="__main__":main()
