"""Export reviewed tracking metrics to root's lab publication contract."""
from pathlib import Path
import hashlib
import json
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/"manifests/source-lock.json").exists())
def load(p):return json.loads(p.read_text(encoding="utf-8"))
def relative(p):return p.relative_to(ROOT).as_posix()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

analysis=load(HERE/"analysis.json")
protocol=load(HERE/"protocol.json")
cases=[]
for c in analysis["cases"]:
    variants=[]
    for v in c["variants"]:
        a,b=v["runs"]
        item={k:a[k] for k in ("run_id","metrics","raw_file","raw_sha256","program_sha256","protocol_sha256","result_file")}
        item.update(variant=v["id"],solver_diagnostics=a["solver_diagnostics"],environment=load(ROOT/a["run"]/"environment.json"))
        item["config"]={"resolved":a["config"]["solver"],"treatment":{"target_mode":a["config"]["target_mode"]},"full_config_file":a["run"]+"/resolved-config.json","full_config_field":None,"protocol_to_api_mapping":a["config"]["protocol_to_api_mapping"]}
        item["reproduction"]={k:b[k] for k in ("run_id","metrics","raw_file","raw_sha256","program_sha256","protocol_sha256","result_file")}
        item["reproduction"].update(tolerances={f:{"atol":protocol["run"]["repeat_tolerance"]["velocity_atol" if f.endswith("qd") else "pose_atol"],"rtol":1e-5} for f in ("body_q","body_qd","joint_q","joint_qd")},checks=v["repeat_checks"],solver_diagnostics=b["solver_diagnostics"])
        variants.append(item)
    conv=[r["solver_diagnostics"]["converged_fraction"] for v in c["variants"] for r in v["runs"]]
    if c["id"].endswith("step_reversal"):
        maxq=max(r["metrics"]["joint_position_reference_max_abs_rad"] for v in c["variants"] for r in v["runs"])
        obs=f"正负目标在2s反向，四次运行最大离散参考角误差 {maxq:.6g} rad；物理验收 {c['status']}。收敛比例范围 {min(conv):.3%}–{max(conv):.3%}，不能从物理吻合推断逐步求解收敛。"
    else:
        ar,br=[v["runs"][0]["metrics"]["steady_tracking_rmse_rad"] for v in c["variants"]]
        obs=f"同传位置/速度正弦参考，POSITION_VELOCITY 与 POSITION 末周期 RMS 为 {ar:.6g}/{br:.6g} rad，前者改善 {1-ar/br:.2%}；物理验收 {c['status']}。POSITION 按实现忽略速度参考而保留阻尼。收敛比例范围 {min(conv):.3%}–{max(conv):.3%}。"
    associations=["model:kamino:joint_target_ke","model:kamino:joint_target_kd","model:kamino:joint_effort_limit"]
    report={"plot":c["plot"],"replay":{"type":"saved_trajectory","time_field":"t","note":"Actual physical seconds; state n+1 follows command n. Raw solver diagnostic arrays are preserved separately from physical acceptance."},"acceptance_results":{"status":c["status"],"criteria":c["criteria"],"paired_checks":c["paired_checks"],"per_run":[{"run_id":r["run_id"],"status":r["status"],"checks":r["checks"]} for v in c["variants"] for r in v["runs"]]},"analysis_file":relative(HERE/"analysis.json")}
    cases.append({"id":c["id"],"record_id":"lab:"+c["id"],"solver":"kamino","title":c["title"],"parameter":"joint_target_ke joint_target_kd joint_effort_limit target_mode","experiment_kind":"mechanism","observation":obs,"physical_acceptance":c["status"],"limitations":c["limitations"]+["Strict solver termination is diagnosed separately; physical pass does not imply every step converged."],"source_refs":c["source_refs"],"associations":associations,"association_relation":"measures_behavior_of","association_scope":"直接测量固定增益/有限力限下的非饱和跟踪机制及target-mode语义；未逐参数扫描kp/kd/力限，不外推任意频率、带宽或步长。","protocol_file":relative(HERE/"protocol.json"),"runner_file":relative(HERE/"runner.py"),"variants":variants,"report":report,"plot":c["plot"]})
publication={"schema_version":"1.0","group":"tracking","formal_runs":analysis["formal_runs"],"protocol_sha256":analysis["protocol_sha256"],"analysis_sha256":sha(HERE/"analysis.json"),"cases":cases,"excluded_runs":analysis["excluded_runs"]}
(HERE/"publication.json").write_text(json.dumps(publication,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
print(json.dumps({"cases":len(cases),"formal_runs":publication["formal_runs"]}))
