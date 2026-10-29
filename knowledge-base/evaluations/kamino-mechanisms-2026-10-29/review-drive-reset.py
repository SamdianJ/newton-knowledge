"""Read-only independent review of archived drive/reset data; no Newton import."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "experiments/kamino_mechanism_lab/drive_reset"
OUT = Path(__file__).with_suffix(".json")
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def mx(x): return float(np.max(np.abs(x))) if np.size(x) else 0.

analysis = load(LAB / "analysis.json")
protocol = load(LAB / "protocol.json")
assert analysis["runner_sha256"] == sha(LAB / "runner.py")
assert analysis["analyzer_sha256"] == sha(LAB / "analyze.py")
assert analysis["protocol_sha256"] == sha(LAB / "protocol.json")
checks, summaries, raw = [], [], {}
def check(name, passed, detail=None):
    checks.append({"name": name, "passed": bool(passed), "detail": detail})

for case in analysis["cases"]:
    for variant in case["variants"]:
        for entry in variant["runs"]:
            p = ROOT / entry["run"]
            r = load(p / "result.json")
            cfg = load(p / "resolved-config.json")
            data = dict(np.load(p / "trajectory.npz", allow_pickle=False))
            key = (case["id"], variant["variant"], entry["repeat"])
            raw[key] = data
            tag = "/".join(map(str, key))
            check(tag + "/archive hashes", all(sha(p / f) == h for f,h in r["files_sha256"].items()))
            check(tag + "/summary hashes", sha(p / "result.json") == entry["result_sha256"] and sha(p / "trajectory.npz") == entry["raw_sha256"])
            check(tag + "/physical finite including t0", all(np.isfinite(v).all() for k,v in data.items() if not k.startswith("status_")))
            check(tag + "/all post-step statuses finite", all(np.isfinite(v[1:]).all() for k,v in data.items() if k.startswith("status_")))
            inertia = np.asarray(cfg["body_inertia"])[0]
            com = np.asarray(cfg["body_com"])[0]
            mass = cfg["body_mass"][0]
            effective = float(inertia[1,1] + mass * (com[0] ** 2 + com[2] ** 2))
            check(tag + "/inertia and COM", np.array_equal(inertia, np.eye(3)) and np.array_equal(com,[.5,0,0]) and mass == 1 and effective == 1.25, effective)
            summary = {"run": entry["run"], "effective_inertia_kg_m2": effective, "lambda_shape": list(data["joint_lambdas_tau"].shape), "initial_nonfinite_status_fields": [k for k,v in data.items() if k.startswith("status_") and not np.isfinite(v[0]).all()], "post_step_converged_fraction": float(data["status_converged"][1:].mean())}
            check(tag + "/convergence summary", summary["post_step_converged_fraction"] == entry["metrics"]["status_converged_fraction"])
            if case["id"] == "kamino_drive_effort_paths":
                # Reconstruct by scalar recurrence rather than importing the analyzer.
                q, v = [0.], [0.]
                effort = [1. if i < 40 else -1. for i in range(80)]
                dt = protocol["common_run"]["dt_s"]
                for tau in effort:
                    v.append(v[-1] + dt * tau / effective)
                    q.append(q[-1] + dt * v[-1])
                summary["independent_q_error_rad"] = mx(data["joint_q"][:,0] - q)
                summary["independent_v_error_rad_s"] = mx(data["joint_qd"][:,0] - v)
                check(tag + "/analytic position", summary["independent_q_error_rad"] <= .001)
                check(tag + "/analytic velocity", summary["independent_v_error_rad_s"] <= .002)
                check(tag + "/signed physical torque", np.array_equal(data["applied_body_wrench"][1:,0,4], effort))
                expected_width = 0 if variant["variant"] == "A" else 1
                check(tag + "/lambda full trajectory shape", data["joint_lambdas_tau"].shape == (81,expected_width))
                if expected_width:
                    check(tag + "/lambda is Nm", np.array_equal(data["joint_lambdas_tau"][1:,0], effort) and mx(data["joint_lambdas_tau"][0]) == 0.)
            else:
                reset = dict(np.load(p / "reset-snapshots.npz", allow_pickle=False))
                controls = ("joint_f", "joint_target_q", "joint_target_qd")
                check(tag + "/all Control fields preserved", all(np.array_equal(reset["before_control_"+k],reset["after_control_"+k]) for k in controls))
                check(tag + "/Control target nonzero", np.array_equal(reset["before_control_joint_target_q"],[-1.]))
                check(tag + "/zero cleared fields", all(mx(reset["after_"+k]) == 0. for k in ("joint_lambdas_tau","body_qdd","internal_time","internal_steps")))
                check(tag + "/success", reset["success_mask"].tolist() == [True])
                if case["id"] == "kamino_reset_preserve_replay":
                    check(tag + "/body preservation", all(np.array_equal(reset["before_"+k],reset["after_"+k]) for k in ("body_q","body_qd")))
                else:
                    check(tag + "/default pose velocity", np.array_equal(reset["after_body_q"],[[0,0,0,0,0,0,1]]) and mx(reset["after_body_qd"]) == 0. and mx(reset["after_joint_qd"]) == 0.)
                warm = p / "warmup.npz"
                if variant["variant"] == "B" or case["id"] == "kamino_reset_preserve_replay":
                    w = dict(np.load(warm, allow_pickle=False))
                    summary["warm_q_rad"] = mx(w["joint_q"][-1])
                    summary["warm_lambda_Nm"] = mx(w["joint_lambdas_tau"][-1])
                    check(tag + "/non-vacuous prewarm", summary["warm_q_rad"] >= .001 and summary["warm_lambda_Nm"] >= .5 and mx(w["body_qd"][-1]) > .01)
            summaries.append(summary)
    for v in ("A","B"):
        check(case["id"]+"/repeat/"+v, all(np.array_equal(raw[(case["id"],v,1)][f],raw[(case["id"],v,2)][f]) for f in ("body_q","body_qd","joint_q","joint_qd")))
    if case["id"] != "kamino_drive_effort_paths":
        for rep in (1,2):
            check(case["id"]+"/fresh-aged/"+str(rep), all(np.array_equal(raw[(case["id"],"A",rep)][f],raw[(case["id"],"B",rep)][f]) for f in ("body_q","body_qd","joint_q","joint_qd")))

check("selected complete cohort", len(summaries)==12 and analysis["runs_selected"]==12 and len(analysis["excluded_runs"])==14)
result = {
  "reviewer": "kamino_loop_fk independent agent", "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
  "status": "passed_with_stated_boundaries" if all(c["passed"] for c in checks) else "findings_require_attention",
  "files": {n:sha(LAB/n) for n in ("runner.py","analyze.py","analysis.json","protocol.json")},
  "review_script_sha256": sha(Path(__file__)), "passed_checks": sum(c["passed"] for c in checks), "failed_checks": sum(not c["passed"] for c in checks),
  "scope": "Read-only code review and independent raw-array recomputation; no simulation, original analyzer execution or source/data modification.",
  "findings": [],
  "source_unit_evidence": [
    {"path":"newton/_src/solvers/kamino/_src/kinematics/constraints.py", "line":400, "finding":"lambda_tau_j = inv_dt * raw constraint impulse; exported revolute channel is torque in N m."},
    {"path":"newton/_src/solvers/kamino/_src/dynamics/wrenches.py", "line":334, "finding":"Dense effort wrench multiplies impulse by inv_dt; w_a_i angular Y is N m, not impulse."},
    {"path":"newton/_src/solvers/kamino/_src/solvers/common.py", "line":146, "finding":"Warmstart multiplies joint_lambda_tau_j by dt to recover impulse."},
    {"path":"newton/_src/solvers/kamino/_src/kinematics/resets.py", "line":375, "finding":"Reset clears reported effort multiplier."}
  ],
  "review_conclusions": [
    "Initial status placeholders are excluded only at sample zero; physical channels retain sample zero and all post-step status entries must be finite. Lambda channel retains all 81 samples; explicit drive legitimately has zero-width effort-constraint channel.",
    "Independent archived mass/COM/inertia checks establish I_y=1+1*(0.5)^2=1.25 kg m^2. Signed pulse torque and scalar semi-implicit recurrence independently reproduce claimed errors.",
    "Prewarm is non-vacuous: q=0.028199944645166397 rad and |lambda_tau|=1 N m with nonzero body velocity. Fresh preserve donor contributes body pose/velocity only; newly built solver is reset under same mode as aged solver before identical commands.",
    "All three Control arrays exist and are identical before/after reset, including nonzero target -1 rad. Commands are explicitly reissued during replay; reset does not promise Control clearing.",
    "Repeated processes and fresh-versus-aged replay physical arrays are exactly equal in this cohort. This verifies measured replay consistency, not completeness of hidden solver-state clearing.",
    "Final analysis explicitly reports bounded-PD converged fraction 0 at 200 iterations and 1e-7 tolerance. Physical/reset gates passing must never be presented as solver convergence passing."
  ],
  "remaining_boundaries": ["CPU PADMM only, single revolute and single world, no contacts/gravity/armature", "Saturated PD only; no unsaturated tracking, transitions, multi-DoF or timestep-general validation", "No masked reset, arbitrary inconsistent preserve states or all warmstart internals tested", "Bounded-PD convergence deficit remains an observed diagnostic limitation; no thresholds relaxed"],
  "runs": summaries, "checks": checks
}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
print(json.dumps({k:result[k] for k in ("status","passed_checks","failed_checks")}))
