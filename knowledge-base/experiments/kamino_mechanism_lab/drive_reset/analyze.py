"""Independently recompute frozen metrics from drive/reset raw arrays."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "manifests/source-lock.json").exists())


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def maximum(a):
    return float(np.max(np.abs(a))) if np.size(a) else 0.0


def compare_arrays(a, b, atol, rtol):
    return {"max_abs": maximum(a - b), "atol": atol, "rtol": rtol, "passed": bool(np.allclose(a, b, atol=atol, rtol=rtol))}


def plot_case(case_id, raw):
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["svg.hashsalt"] = "kamino-drive-reset-frozen-v1"
    import matplotlib.pyplot as plt
    a, b = raw[("A", 1)], raw[("B", 1)]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.4), constrained_layout=True)
    for label, data in (("A", a), ("B", b)):
        axes[0].plot(data["time"], data["joint_q"][:, 0], label=label, linestyle="--" if label == "B" else "-")
        axes[1].plot(data["time"], data["joint_qd"][:, 0], label=label, linestyle="--" if label == "B" else "-")
    axes[0].set_ylabel("Joint angle [rad]")
    axes[1].set_ylabel("Joint velocity [rad/s]")
    if case_id == "kamino_drive_effort_paths":
        axes[2].plot(a["time"][1:], a["applied_body_wrench"][1:, 0, 4], label="A actual")
        axes[2].plot(b["time"][1:], b["joint_lambdas_tau"][1:, 0], label="B reported", linestyle="--")
        axes[2].set_ylabel("Applied drive effort [N m]")
    else:
        axes[2].plot(a["time"], np.max(np.abs(a["body_q"] - b["body_q"]), axis=(1, 2)), label="body pose max abs")
        axes[2].plot(a["time"], np.max(np.abs(a["body_qd"] - b["body_qd"]), axis=(1, 2)), label="body velocity max abs")
        axes[2].set_ylabel("Componentwise difference (mixed units)")
    for axis in axes:
        axis.set_xlabel("Replay time [s]")
        axis.grid(alpha=.25)
        axis.legend()
    fig.suptitle(case_id + " | repeat 1; see table for repeat 2")
    output = HERE / (case_id + ".svg")
    fig.savefig(output, metadata={"Date": None})
    plt.close(fig)
    return output.relative_to(ROOT).as_posix()


def main():
    protocol = load(HERE / "protocol.json")
    protocol_hash, runner_hash = sha(HERE / "protocol.json"), sha(HERE / "runner.py")
    revisions = {r["runner_sha256"]: r for r in load(HERE / "harness-revisions.json")["revisions"]}
    records, excluded = [], []
    for path in sorted((HERE / "runs").glob("*/result.json")):
        r = load(path)
        if r["status"] == "completed" and r["protocol_sha256"] == protocol_hash and r["runner_sha256"] == runner_hash:
            r["path"] = path.parent
            records.append(r)
        else:
            revision = revisions.get(r["runner_sha256"], {})
            excluded.append({"run": path.parent.relative_to(ROOT).as_posix(), "status": r["status"], "classification": revision.get("classification", "excluded"), "reason": r.get("error", revision.get("change", "Different runner; preserved, not selected")), "runner_sha256": r["runner_sha256"]})
    cases = []
    global_checks = []
    for spec in protocol["cases"]:
        output = {"id": spec["id"], "title": spec["title"], "criteria": spec["criteria"], "variants": [], "paired_checks": [], "limitations": spec["limitations"], "source_refs": protocol["source_refs"]}
        raw = {}
        for variant in ("A", "B"):
            runs = sorted([r for r in records if r["case"] == spec["id"] and r["variant"] == variant], key=lambda r: r["repeat"])
            if len(runs) != 2 or [r["repeat"] for r in runs] != [1, 2]:
                raise ValueError(f"Expected exactly repeats 1,2 under current runner: {spec['id']} {variant}")
            variant_out = {"variant": variant, "runs": [], "repeat_checks": {}}
            for run in runs:
                path = run["path"]
                arrays = dict(np.load(path / "trajectory.npz", allow_pickle=False))
                raw[(variant, run["repeat"])] = arrays
                cfg = load(path / "resolved-config.json")
                src = load(path / "installed-source-validation.json")
                checks = []
                metrics = {}

                def check(name, actual, expected, passed):
                    checks.append({"name": name, "actual": actual, "expected": expected, "passed": bool(passed)})

                def upper(name, actual, limit):
                    metrics[name] = actual
                    check(name, actual, {"max": limit}, actual <= limit)

                check("file hashes", len(run["files_sha256"]), "all archived files match result", all(sha(path / k) == h for k, h in run["files_sha256"].items()))
                check("installed pinned Python sources", src["checked_python_files"], "no missing/changed files", not src["missing"] and not src["changed"] and src["checked_python_files"] > 800)
                finite = all(np.isfinite(v[1:] if k.startswith("status_") else v).all() for k, v in arrays.items())
                check("all raw trajectory floats finite", bool(finite), True, finite)
                check("samples", len(arrays["time"]), 81, len(arrays["time"]) == 81)
                check("full physical model mass", cfg["body_mass"], [1.0], np.allclose(cfg["body_mass"], [1.0], atol=1e-7))
                criteria = spec["criteria"]
                if spec["id"] == "kamino_drive_effort_paths":
                    dt = protocol["common_run"]["dt_s"]
                    tau = np.r_[np.ones(40), -np.ones(40)]
                    velocity = np.r_[0., np.cumsum(tau * dt / 1.25)]
                    position = np.r_[0., np.cumsum(velocity[1:] * dt)]
                    continuous = position - .5 * dt * velocity
                    actual_q, actual_qd = arrays["joint_q"][:, 0], arrays["joint_qd"][:, 0]
                    applied = arrays["applied_body_wrench"][1:, 0, 4]
                    upper("joint_velocity_reference_max_abs_rad_s", maximum(actual_qd - velocity), criteria["joint_velocity_reference_max_abs_rad_s"])
                    upper("joint_position_euler_reference_max_abs_rad", maximum(actual_q - position), criteria["joint_position_euler_reference_max_abs_rad"])
                    upper("applied_effort_signed_max_abs_error_Nm", maximum(applied - tau), criteria["applied_effort_signed_max_abs_error_Nm"])
                    upper("applied_effort_max_Nm", maximum(applied), criteria["applied_effort_max_Nm"])
                    upper("joint_anchor_origin_max_norm_m", float(np.linalg.norm(arrays["body_q"][:, 0, :3], axis=1).max()), criteria["joint_anchor_origin_max_norm_m"])
                    expected_path = criteria["routing_" + variant + "_dof_act_paths"]
                    check("actual drive routing", cfg["dof_act_paths"], expected_path, cfg["dof_act_paths"] == expected_path)
                    if variant == "B":
                        upper("bounded_reported_effort_max_error_Nm", maximum(arrays["joint_lambdas_tau"][1:, 0] - tau), criteria["bounded_reported_effort_max_error_Nm"])
                    metrics.update(continuous_time_position_max_error_rad=maximum(actual_q - continuous), positive_effort_mean_Nm=float(applied[:40].mean()), negative_effort_mean_Nm=float(applied[40:].mean()), actual_final_q_rad=float(actual_q[-1]), actual_final_qd_rad_s=float(actual_qd[-1]), analytical_effective_inertia_kg_m2=1.25)
                    np.savez_compressed(path.parent.parent / (path.name + "-reference.npz"), time=arrays["time"], joint_q_euler=position, joint_q_continuous=continuous, joint_qd=velocity, commanded_saturated_effort=tau)
                else:
                    reset = dict(np.load(path / "reset-snapshots.npz", allow_pickle=False))
                    warm_path = path / "warmup.npz"
                    if variant == "B" or spec["id"] == "kamino_reset_preserve_replay":
                        check("required non-vacuous warmup saved", warm_path.exists(), True, warm_path.exists())
                    if warm_path.exists():
                        warm = dict(np.load(warm_path, allow_pickle=False))
                        for key, field in (("warmup_abs_q_min_rad", "joint_q"), ("warmup_abs_lambda_min_Nm", "joint_lambdas_tau")):
                            value = maximum(warm[field][-1])
                            metrics[key.replace("min", "actual")] = value
                            check(key, value, {"min": criteria[key]}, value >= criteria[key])
                    if spec["id"] == "kamino_reset_default_replay":
                        initial = np.array([[0., 0., 0., 0., 0., 0., 1.]])
                        upper("reset_body_pose_max_abs_from_initial", maximum(reset["after_body_q"] - initial), criteria["reset_body_pose_max_abs_from_initial"])
                        upper("reset_body_velocity_max_abs", maximum(reset["after_body_qd"]), criteria["reset_body_velocity_max_abs"])
                        upper("reset_joint_velocity_max_abs", maximum(reset["after_joint_qd"]), criteria["reset_joint_velocity_max_abs"])
                    else:
                        upper("preserved_body_pose_max_abs_error", maximum(reset["after_body_q"] - reset["before_body_q"]), criteria["preserved_body_pose_max_abs_error"])
                        upper("preserved_body_velocity_max_abs_error", maximum(reset["after_body_qd"] - reset["before_body_qd"]), criteria["preserved_body_velocity_max_abs_error"])
                    for key, field in (("reset_joint_effort_max_abs", "joint_lambdas_tau"), ("reset_body_acceleration_max_abs", "body_qdd"), ("reset_internal_time_max_abs", "internal_time")):
                        upper(key, maximum(reset["after_" + field]), criteria[key])
                    check("reset_internal_steps", int(maximum(reset["after_internal_steps"])), 0, maximum(reset["after_internal_steps"]) == 0)
                    control_keys = [k.removeprefix("before_") for k in reset if k.startswith("before_control_")]
                    unchanged = all(np.array_equal(reset["before_" + k], reset["after_" + k]) for k in control_keys)
                    check("control_unchanged", unchanged, True, unchanged)
                    check("success_mask", reset["success_mask"].tolist(), [True], bool(reset["success_mask"].all()))
                metrics["status_converged_fraction"] = float(arrays["status_converged"][1:].mean())
                metrics["status_iterations_max"] = int(arrays["status_iterations"][1:].max())
                metrics["terminal_residuals"] = {k: float(arrays["status_" + k][-1, 0]) for k in ("r_p", "r_d", "r_c")}
                status = "passed" if all(c["passed"] for c in checks) else "failed_criteria"
                variant_out["runs"].append({"run": path.relative_to(ROOT).as_posix(), "repeat": run["repeat"], "status": status, "metrics": metrics, "checks": checks, "raw_file": (path / "trajectory.npz").relative_to(ROOT).as_posix(), "raw_sha256": run["raw_sha256"], "result_sha256": sha(path / "result.json"), "protocol_sha256": protocol_hash, "runner_sha256": runner_hash})
                global_checks += checks
            tolerance = protocol["common_run"]["repeat_tolerance"]
            for field in ("body_q", "joint_q", "body_qd", "joint_qd"):
                atol = tolerance["velocity_atol"] if field.endswith("qd") else tolerance["pose_atol"]
                value = compare_arrays(raw[(variant, 1)][field], raw[(variant, 2)][field], atol, tolerance["rtol"])
                variant_out["repeat_checks"][field] = value
                global_checks.append({"name": spec["id"] + "/" + variant + " repeat " + field, **value})
            output["variants"].append(variant_out)
        if spec["id"] != "kamino_drive_effort_paths":
            for repeat in (1, 2):
                pair = {"repeat": repeat, "fields": {}}
                for field in ("body_q", "joint_q", "body_qd", "joint_qd"):
                    atol = spec["criteria"]["paired_replay_velocity_max_abs"] if field.endswith("qd") else spec["criteria"]["paired_replay_pose_max_abs"]
                    value = compare_arrays(raw[("A", repeat)][field], raw[("B", repeat)][field], atol, spec["criteria"]["paired_replay_rtol"])
                    pair["fields"][field] = value
                    global_checks.append({"name": spec["id"] + f" pair r{repeat} " + field, **value})
                output["paired_checks"].append(pair)
        output["status"] = "passed" if all(r["status"] == "passed" for v in output["variants"] for r in v["runs"]) and all(c["passed"] for v in output["variants"] for c in v["repeat_checks"].values()) and all(c["passed"] for p in output["paired_checks"] for c in p["fields"].values()) else "failed_criteria"
        output["metrics"] = {"run_metrics": [{"variant": v["variant"], "repeat": r["repeat"], **r["metrics"]} for v in output["variants"] for r in v["runs"]], "replay": output["paired_checks"]}
        output["plot"] = plot_case(spec["id"], raw)
        output["solver_status_summary"] = {v["variant"]: [r["metrics"]["status_converged_fraction"] for r in v["runs"]] for v in output["variants"]}
        if spec["id"] == "kamino_drive_effort_paths":
            output["observation"] = "两种驱动路径均把正反请求限制为 ±1 N·m，转角/角速度吻合独立有效惯量参考。显式路径 terminal converged=100%；有界隐式PD在冻结的1e-7容差下为0%，到达200迭代预算。物理验收通过不等于该收敛标志通过。"
        else:
            output["observation"] = "形成非零运动和乘子历史后，所测reset模式与fresh参考的重放、独立进程重复在保存数组中一致；Control保持不变且重放前显式重发命令。有界PD terminal converged=0%，reset和物理一致性通过不构成求解收敛保证。"
        output["limitations"].append("Bounded-PD terminal convergence stayed false under the frozen 1e-7 tolerances and 200-iteration budget; terminal status was diagnostic, not an acceptance gate. No thresholds were relaxed.")
        if output["status"] != "passed":
            output["observation"] = "至少一个冻结指标失败；保留负结果，不放宽阈值。"
        cases.append(output)
    result = {"status": "passed" if all(c["status"] == "passed" for c in cases) else "failed_criteria", "protocol_sha256": protocol_hash, "runner_sha256": runner_hash, "analyzer_sha256": sha(__file__), "runs_selected": len(records), "passed_checks": sum(c["passed"] for c in global_checks), "failed_checks": sum(not c["passed"] for c in global_checks), "cases": cases, "excluded_runs": excluded, "independent_analysis": "NumPy analytic rotor impulse and geometry; file/hash and repeated/fresh-vs-reset checks. No Newton import or simulation in this analyzer."}
    (HERE / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("cases", "excluded_runs")}, ensure_ascii=False))
    print(json.dumps([{ "id": c["id"], "status": c["status"]} for c in cases]))


if __name__ == "__main__":
    main()
